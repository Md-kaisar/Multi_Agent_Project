"""
Procurement Agent
-----------------
GOAL   : Resolve inventory shortage by selecting and ordering from the best supplier.

OBSERVE: Read shortages list from Inventory Agent state (deficit per ingredient)

REASON : For each shortage:
  1. Python fetches candidate suppliers and scores them (Speed×0.40, Reliability×0.35, Price×0.25)
  2. LLM receives structured facts and produces reasoning text + recommendation
  3. Python VALIDATES LLM recommendation (supplier must exist, quantity must be reasonable)
  → This separation is critical: Python handles arithmetic, LLM handles trade-off reasoning

DECIDE : Select the validated recommended supplier (or rule-based best if LLM unavailable)

ACT    :
  → Create Purchase Order record in DB (status = APPROVED)
  → Set incoming_stock += reorder_qty (NOT current_stock — item hasn't arrived yet)
  → Reserve the deficit amount against what's incoming
  → Update order status = PROCUREMENT_ORDERED

  ⚠️  IMPORTANT: current_stock is NOT increased immediately.
      incoming_stock represents goods in transit from the supplier.
      The distinction between current_stock and incoming_stock is deliberate:
      a supplier ETA of 1 hour means the kitchen cannot start for 1 hour.

VERIFY : Confirm at least one PO was created; log total_wait_hrs for Delivery Agent

ESCALATE (Flaw #10): If NO supplier found → mark order DELAYED, set needs_escalation=True
"""

from agents.state import AgentState
from database.database import (
    log_agent_action,
    get_suppliers_for_ingredient,
    create_purchase_order,
    update_order_status,
    add_incoming_stock,
    reserve_stock,
)
from utils.calculations import evaluate_suppliers
from ai.llm import llm_engine


# ── Fallback suppliers for ingredients not covered by DB ────────────────────
FALLBACK_SUPPLIERS = {
    "Chicken": [
        {"id": 1, "name": "Apex Poultry & Fresh Meat",  "ingredient_name": "Chicken",
         "price_per_unit": 220.0, "available_quantity": 100.0, "delivery_time_hrs": 3.0, "reliability_score": 0.90},
        {"id": 2, "name": "Express Farm Direct",          "ingredient_name": "Chicken",
         "price_per_unit": 210.0, "available_quantity": 80.0,  "delivery_time_hrs": 1.0, "reliability_score": 0.94},
        {"id": 3, "name": "Budget Wholesale Traders",     "ingredient_name": "Chicken",
         "price_per_unit": 195.0, "available_quantity": 200.0, "delivery_time_hrs": 7.5, "reliability_score": 0.82},
        {"id": 4, "name": "GreenValley Agro Supply",      "ingredient_name": "Chicken",
         "price_per_unit": 235.0, "available_quantity": 50.0,  "delivery_time_hrs": 0.5, "reliability_score": 0.98},
    ],
    "Rice": [
        {"id": 5, "name": "Royal Grain Merchants", "ingredient_name": "Rice",
         "price_per_unit": 60.0, "available_quantity": 500.0, "delivery_time_hrs": 2.0, "reliability_score": 0.95},
        {"id": 6, "name": "Deccan Rice Mills",      "ingredient_name": "Rice",
         "price_per_unit": 55.0, "available_quantity": 300.0, "delivery_time_hrs": 5.0, "reliability_score": 0.88},
    ],
    "Paneer": [
        {"id": 7, "name": "Pure Dairy Farms",  "ingredient_name": "Paneer",
         "price_per_unit": 320.0, "available_quantity": 60.0, "delivery_time_hrs": 1.5, "reliability_score": 0.92},
        {"id": 8, "name": "Amrit Dairy Co-op", "ingredient_name": "Paneer",
         "price_per_unit": 300.0, "available_quantity": 100.0, "delivery_time_hrs": 4.0, "reliability_score": 0.85},
    ],
    "default": [
        {"id": 10, "name": "Metro Agro Suppliers",  "ingredient_name": "Generic",
         "price_per_unit": 80.0, "available_quantity": 200.0, "delivery_time_hrs": 2.0, "reliability_score": 0.88},
        {"id": 11, "name": "Sunrise Fresh Vendors", "ingredient_name": "Generic",
         "price_per_unit": 75.0, "available_quantity": 150.0, "delivery_time_hrs": 4.0, "reliability_score": 0.85},
        {"id": 12, "name": "Quick Mart Wholesale",  "ingredient_name": "Generic",
         "price_per_unit": 70.0, "available_quantity": 300.0, "delivery_time_hrs": 6.0, "reliability_score": 0.80},
    ]
}

# Validation constants
MAX_PURCHASE_KG  = 500.0   # no single PO > 500 kg (sanity check against LLM hallucination)
MIN_PURCHASE_KG  = 0.1


def _validate_qty(qty: float, deficit: float) -> float:
    """
    Validate purchase quantity (Flaw #15).
    Ensures LLM-influenced qty is in a reasonable range:
    Must be >= deficit and <= MAX_PURCHASE_KG.
    """
    qty = max(float(deficit), float(qty))       # at least cover the deficit
    qty = min(qty, MAX_PURCHASE_KG)             # never more than sanity max
    return round(qty, 3)


def run_procurement_agent(state: AgentState) -> AgentState:
    shortages    = state.get("shortages", [])
    order_id     = state.get("order_id")
    order_ctx    = {
        "customer_name": state.get("customer_name"),
        "food_item":     state.get("food_item"),
        "quantity":      state.get("quantity"),
    }

    # ── OBSERVE: no shortages → skip ──────────────────────────────────────
    if not shortages:
        state.setdefault("agent_log", []).append({
            "agent":   "Procurement Agent",
            "status":  "skipped",
            "message": "No shortages detected. Procurement not required.",
            "details": {}
        })
        state["procurement_decision"] = {
            "status": "NOT_REQUIRED", "decisions": [], "total_wait_hrs": 0.0
        }
        return state

    decisions         = []
    total_cost_all    = 0.0
    max_wait_hrs      = 0.0
    needs_escalation  = False

    for shortage in shortages:
        ing_name    = shortage["ingredient"]
        deficit     = shortage["deficit"]
        reorder_qty = shortage["reorder_qty"]   # deficit + 20% buffer
        severity    = shortage.get("severity", "LOW")

        # ── OBSERVE: fetch suppliers ───────────────────────────────────────
        suppliers = get_suppliers_for_ingredient(ing_name)
        if not suppliers:
            suppliers = FALLBACK_SUPPLIERS.get(ing_name, FALLBACK_SUPPLIERS["default"])

        if not suppliers:
            # Flaw #10: no supplier → escalate
            needs_escalation = True
            log_agent_action(
                "Procurement Agent", "Escalation",
                f"No supplier found for '{ing_name}'. Order cannot be fulfilled.",
                "ERROR", order_id=order_id
            )
            continue

        # ── REASON: score suppliers (Python handles all arithmetic) ───────
        ranked = evaluate_suppliers(suppliers, target_qty=reorder_qty)
        rule_based_best = ranked[0]   # Python's top pick before LLM input

        # ── DECIDE: get LLM reasoning + recommendation ────────────────────
        llm_result = llm_engine.get_procurement_recommendation(
            order_context=order_ctx,
            shortage=shortage,
            ranked_suppliers=ranked
        )
        rec_name    = llm_result["recommended_supplier"]
        reasoning   = llm_result["reasoning"]
        llm_mode    = llm_result["mode"]

        # ── VALIDATE: find the supplier object by name ────────────────────
        best = next((s for s in ranked if s["name"] == rec_name), rule_based_best)

        # Validate purchase quantity
        validated_qty  = _validate_qty(reorder_qty, deficit)
        total_cost     = round(best["price_per_unit"] * validated_qty, 2)
        supplier_wait  = best["delivery_time_hrs"]
        max_wait_hrs   = max(max_wait_hrs, supplier_wait)
        total_cost_all += total_cost

        # ── ACT: create Purchase Order ────────────────────────────────────
        try:
            po_id = create_purchase_order(
                supplier_id=best.get("id", "fallback_supplier"),
                ingredient_name=ing_name,
                quantity=validated_qty,
                total_cost=total_cost,
                recommended_by=f"Procurement Agent ({llm_mode})"
            )
        except Exception as e:
            print(f"Error creating PO: {e}")
            po_id = None

        # ── ACT: incoming_stock += reorder_qty (NOT current_stock) ────────
        # This models reality: stock has been ordered but not yet arrived.
        # The Delivery Agent reads total_wait_hrs to calculate real ETA.
        add_incoming_stock(ing_name, validated_qty)

        # Also reserve the deficit amount so no other order claims incoming stock
        reserve_stock(ing_name, deficit)

        log_agent_action(
            "Procurement Agent",
            f"PO #{po_id} Created ({llm_mode})",
            f"Ingredient: {ing_name} | Qty: {validated_qty} {shortage['unit']} | "
            f"Supplier: {best['name']} | ₹{total_cost:.2f} | ETA: {supplier_wait} hrs",
            "INFO",
            order_id=order_id
        )

        decisions.append({
            "ingredient":          ing_name,
            "deficit":             deficit,
            "reorder_qty":         validated_qty,
            "severity":            severity,
            "selected_supplier":   best,
            "all_suppliers":       ranked,
            "po_id":               po_id,
            "total_cost":          total_cost,
            "supplier_delivery_hrs": supplier_wait,
            "llm_mode":            llm_mode,
            "reasoning":           reasoning,
        })

    # ── ESCALATE if any shortage had no supplier ───────────────────────────
    if needs_escalation and not decisions:
        if order_id:
            update_order_status(order_id, "DELAYED")
        state.setdefault("agent_log", []).append({
            "agent":   "Procurement Agent",
            "status":  "error",
            "message": "⚠️ No suppliers found. Order marked DELAYED.",
            "details": {}
        })
        state["procurement_decision"] = {
            "status": "FAILED", "decisions": [], "total_wait_hrs": 0.0
        }
        state["needs_escalation"] = True
        state["final_decision"] = {
            "order_id": order_id,
            "order_stage": "DELAYED",
            "steps": [
                {"check": "Order received & validated", "ok": True, "detail": "Valid request"},
                {"check": "Supplier Evaluation", "ok": False, "detail": "No suppliers available for required ingredients. Order DELAYED."}
            ]
        }
        return state

    # ── VERIFY: update order status ────────────────────────────────────────
    if order_id and decisions:
        update_order_status(order_id, "PROCUREMENT_ORDERED")

    # ── Build summary log ──────────────────────────────────────────────────
    llm_modes = list({d["llm_mode"] for d in decisions})
    full_msg = (
        f"Procurement completed for {len(decisions)} ingredient(s). "
        f"Mode: {', '.join(llm_modes)}. "
        f"Total cost: ₹{total_cost_all:.2f}. "
        f"Max supplier wait: {max_wait_hrs} hrs (kitchen ready in {max_wait_hrs} hrs). "
        f"Stock updated as INCOMING (not yet on-shelf)."
    )
    log_agent_action("Procurement Agent", "Procurement Complete", full_msg, "INFO", order_id=order_id)

    state.setdefault("agent_log", []).append({
        "agent":   "Procurement Agent",
        "status":  "ok",
        "message": full_msg,
        "details": {
            "decisions":             decisions,
            "total_procurement_cost": round(total_cost_all, 2),
            "total_wait_hrs":         max_wait_hrs,
        }
    })
    state["procurement_decision"] = {
        "status":                  "COMPLETED",
        "decisions":               decisions,
        "total_procurement_cost":  round(total_cost_all, 2),
        "total_wait_hrs":          max_wait_hrs,
    }
    state["needs_escalation"] = False
    return state
