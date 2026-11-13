"""
Inventory Agent
---------------
GOAL   : Determine whether the order can be fulfilled from current stock.

OBSERVE: Read available_stock = current_stock − reserved_stock from DB
         (reserved_stock prevents overselling of the same physical stock)

REASON : For each required ingredient, compare available_stock vs required_qty
         Classify severity of any shortage

DECIDE : needs_procurement = True if ANY ingredient cannot be fulfilled

ACT    :
  → If STOCK SUFFICIENT:
      reserve_stock(ingredient, consumed) — locks stock for this order
      Update order status = CONFIRMED
  → If SHORTAGE:
      Update order status = AWAITING_PROCUREMENT

VERIFY : Confirm shortages list is accurate before passing to next agent

IMPORTANT: The agent uses available_stock (current − reserved), NOT current_stock.
           This prevents two simultaneous orders from claiming the same stock.
"""

from agents.state import AgentState
from database.database import (
    log_agent_action, get_inventory_details, update_order_status, reserve_stock
)


def _classify_shortage(available: float, required: float, min_stock: float) -> str:
    """
    Called ONLY when available < required (i.e., order cannot be fulfilled).
    CRITICAL = completely out, or below safety threshold.
    LOW       = has some stock but insufficient for this order.
    """
    if available <= 0:
        return "CRITICAL"
    if available < min_stock:
        return "CRITICAL"
    return "LOW"


def run_inventory_agent(state: AgentState) -> AgentState:
    order_id     = state.get("order_id")
    requirements = state["ingredient_requirements"]   # {ing_name: qty_needed}
    food_item    = state.get("food_item", "Item")

    # ── OBSERVE: read full inventory with available_stock ──────────────────
    inventory = get_inventory_details()
    # Build lookup by ingredient name
    stock_map = {row["ingredient_name"]: row for row in inventory}

    shortages   = []
    audit_lines = []
    all_ok      = True

    # ── REASON: compare available_stock vs each required ingredient ────────
    for ing_name, required_qty in requirements.items():
        row             = stock_map.get(ing_name)
        available_stock = row["available_stock"] if row else 0.0   # current − reserved
        current_stock   = row["current_stock"]   if row else 0.0
        reserved_stock  = row["reserved_stock"]  if row else 0.0
        incoming_stock  = row["incoming_stock"]  if row else 0.0
        min_stock       = row["min_stock"]       if row else 0.0
        unit            = row["unit"]            if row else "kg"

        if available_stock < required_qty:
            # SHORTAGE — cannot fulfil this ingredient
            all_ok      = False
            deficit     = round(required_qty - available_stock, 3)
            severity    = _classify_shortage(available_stock, required_qty, min_stock)
            reorder_qty = round(deficit * 1.20, 3)   # deficit + 20% safety buffer

            shortages.append({
                "ingredient":    ing_name,
                "required":      required_qty,
                "available":     available_stock,
                "current_stock": current_stock,
                "reserved":      reserved_stock,
                "incoming":      incoming_stock,
                "deficit":       deficit,
                "reorder_qty":   reorder_qty,
                "unit":          unit,
                "severity":      severity,
                "min_stock":     min_stock,
            })

            icon = "🔴" if severity == "CRITICAL" else "⚠️"
            audit_lines.append(
                f"{icon} {ing_name}: available={available_stock} {unit} "
                f"(current={current_stock} − reserved={reserved_stock}) | "
                f"required={required_qty} {unit} | deficit={deficit} {unit} [{severity}]"
            )
        else:
            # SUFFICIENT
            audit_lines.append(
                f"✓  {ing_name}: available={available_stock} {unit} "
                f"(current={current_stock} − reserved={reserved_stock}) | "
                f"required={required_qty} {unit} | OK"
            )

    needs_proc = len(shortages) > 0

    # ── ACT: update DB based on decision ──────────────────────────────────
    if order_id:
        if not needs_proc:
            # Stock sufficient → CONFIRM and reserve consumed quantities
            update_order_status(order_id, "CONFIRMED")
            for ing_name, consumed in requirements.items():
                reserve_stock(ing_name, consumed)
            audit_lines.append(
                "\n✅ DECISION: All ingredients available. Stock reserved. "
                "Order CONFIRMED → routing to Delivery Agent."
            )
        else:
            update_order_status(order_id, "AWAITING_PROCUREMENT")
            shortage_summary = "; ".join(
                f"{s['ingredient']} [{s['severity']}]: need {s['reorder_qty']} {s['unit']}"
                for s in shortages
            )
            audit_lines.append(
                f"\n⚠️ DECISION: Shortage detected ({shortage_summary}). "
                "Order status → AWAITING_PROCUREMENT. Routing to Procurement Agent."
            )

    # ── VERIFY & LOG ───────────────────────────────────────────────────────
    full_msg = "\n".join(audit_lines)
    log_agent_action(
        "Inventory Agent",
        f"Stock Audit → {'AWAITING_PROCUREMENT' if needs_proc else 'CONFIRMED'}",
        full_msg,
        "WARNING" if needs_proc else "INFO",
        order_id=order_id
    )

    log = state.get("agent_log", [])
    log.append({
        "agent":   "Inventory Agent",
        "status":  "warning" if needs_proc else "ok",
        "message": full_msg,
        "details": {
            "shortages":       shortages,
            "stock_map":       {k: v["available_stock"] for k, v in stock_map.items()},
            "needs_procurement": needs_proc,
        }
    })

    state["inventory_snapshot"] = inventory
    state["shortages"]          = shortages
    state["needs_procurement"]  = needs_proc
    state["agent_log"]          = log
    return state
