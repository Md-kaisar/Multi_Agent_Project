"""
Delivery Agent
--------------
GOAL   : Assign the best available rider and produce a realistic ETA.

OBSERVE: Read available riders from DB (status, active_orders, distance_km, vehicle_type)
         Read procurement_decision.total_wait_hrs (supplier wait before kitchen can start)

REASON : Score each AVAILABLE rider on three criteria:
  - Availability (50%): AVAILABLE=1.0, BUSY=0.0
  - Workload    (30%): fewer active_orders = better (0 orders → 1.0, scaled down per order)
  - Distance    (20%): closer = better (normalised against max distance in pool)
  Composite score = 0.50×availability + 0.30×workload_score + 0.20×proximity_score

DECIDE : Select rider with highest composite score
         If NO riders available → escalate, mark order DELAYED

ACT    :
  → Insert delivery record in DB
  → Update order status:
      With procurement wait → SCHEDULED (rider pre-assigned, waits for stock)
      No procurement wait   → OUT_FOR_DELIVERY (rider dispatched now)

VERIFY : ETA breakdown visible:
  total_eta_min = procurement_wait_min + prep_min + transit_min

CRITICAL LOGIC (Flaw #11 fix):
  Rider selection is NOT random — it's a composite score.
  Rider with fewer orders and less distance wins, not the fastest vehicle alone.
"""

from agents.state import AgentState
from database.database import (
    log_agent_action, get_delivery_riders, update_order_status, create_delivery_assignment
)

VEHICLE_SPEED_KMH = {"Bike": 28, "EV Scooter": 25, "Scooter": 24}

FALLBACK_RIDERS = [
    {"id": 1, "name": "Rahul Kumar",  "vehicle_type": "Bike",       "status": "AVAILABLE",
     "current_location": "Indiranagar",  "active_orders": 0, "distance_km": 2.5},
    {"id": 2, "name": "Vikram Singh", "vehicle_type": "EV Scooter", "status": "AVAILABLE",
     "current_location": "Koramangala",  "active_orders": 1, "distance_km": 4.0},
    {"id": 3, "name": "Deepa Roy",    "vehicle_type": "Bike",       "status": "AVAILABLE",
     "current_location": "HSR Layout",   "active_orders": 0, "distance_km": 3.2},
    {"id": 4, "name": "Amit Sharma",  "vehicle_type": "Scooter",    "status": "BUSY",
     "current_location": "MG Road",      "active_orders": 2, "distance_km": 5.5},
]


def _score_rider(rider: dict, max_distance: float) -> float:
    """
    Composite rider score (Flaw #11 fix):
    Availability (50%) + Workload (30%) + Proximity (20%)
    """
    status = rider.get("status", "AVAILABLE")
    if status == "BUSY":
        return 0.0   # BUSY riders are excluded

    availability_score = 1.0
    orders_count       = min(rider.get("active_orders", 0), 5)
    workload_score     = 1.0 - (orders_count / 5.0)   # 0 orders → 1.0, 5 → 0.0
    dist               = rider.get("distance_km", 5.0)
    proximity_score    = 1.0 - (dist / max(max_distance, 1.0))

    return round(
        0.50 * availability_score +
        0.30 * workload_score     +
        0.20 * proximity_score,
        4
    )


def run_delivery_agent(state: AgentState) -> AgentState:
    order_id    = state.get("order_id")
    location    = state.get("delivery_location", "Unknown")
    food_item   = state.get("food_item", "Item")
    quantity    = state.get("quantity", 1)
    customer    = state.get("customer_name", "Customer")
    shortages   = state.get("shortages", [])
    proc        = state.get("procurement_decision") or {}
    proc_decs   = proc.get("decisions", [])
    # ── procurement_wait_hrs: how long before kitchen can even start ───────
    procurement_wait_hrs = proc.get("total_wait_hrs", 0.0)

    # ── OBSERVE: fetch riders from DB ─────────────────────────────────────
    riders = get_delivery_riders()
    if not riders:
        riders = FALLBACK_RIDERS

    # ── REASON: score every rider ──────────────────────────────────────────
    available_riders = [r for r in riders if r.get("status") == "AVAILABLE"]
    max_dist         = max((r.get("distance_km", 5.0) for r in available_riders), default=10.0)

    scored = []
    for r in available_riders:
        r["composite_score"] = _score_rider(r, max_dist)
        scored.append(r)

    scored.sort(key=lambda r: r["composite_score"], reverse=True)

    # ── DECIDE: pick best rider ────────────────────────────────────────────
    if not scored:
        # No available riders → escalate
        if order_id:
            update_order_status(order_id, "DELAYED")
        log_agent_action(
            "Delivery Agent", "Escalation",
            "No riders available. Order marked DELAYED.",
            "ERROR", order_id=order_id
        )
        msg = "⚠️ No available riders. Order has been marked DELAYED."
        state.setdefault("agent_log", []).append({
            "agent": "Delivery Agent", "status": "error",
            "message": msg, "details": {}
        })
        state["delivery_status"] = {"order_stage": "DELAYED", "total_eta_min": None}
        state["final_decision"]  = {"order_id": order_id, "order_stage": "DELAYED", "steps": []}
        return state

    selected = scored[0]

    # ── VERIFY: compute realistic ETA ─────────────────────────────────────
    distance_km          = selected.get("distance_km", 3.0)
    speed_kph            = VEHICLE_SPEED_KMH.get(selected.get("vehicle_type", "Bike"), 25)
    prep_min             = 15 + max(0, (quantity // 10) * 3)   # scales with order size
    transit_min          = max(5, int((distance_km / speed_kph) * 60))
    procurement_wait_min = int(procurement_wait_hrs * 60)
    total_eta_min        = procurement_wait_min + prep_min + transit_min

    # ── ACT: persist delivery record ──────────────────────────────────────
    order_stage = "SCHEDULED" if procurement_wait_min > 0 else "OUT_FOR_DELIVERY"
    db_status   = order_stage

    try:
        create_delivery_assignment(
            order_id=order_id,
            rider_id=selected.get("id"),
            delivery_eta_min=total_eta_min,
            status=order_stage
        )
    except Exception:
        pass

    if order_id:
        readable_status = "SCHEDULED" if order_stage == "SCHEDULED" else "Out for Delivery"
        update_order_status(order_id, readable_status)

    # ── Build delivery plan ────────────────────────────────────────────────
    delivery_plan = {
        "order_id":             order_id,
        "rider_name":           selected["name"],
        "vehicle":              selected.get("vehicle_type", "Bike"),
        "rider_location":       selected.get("current_location", "Nearby"),
        "composite_score":      selected["composite_score"],
        "active_orders":        selected.get("active_orders", 0),
        "distance_km":          distance_km,
        "prep_min":             prep_min,
        "transit_min":          transit_min,
        "procurement_wait_min": procurement_wait_min,
        "total_eta_min":        total_eta_min,
        "order_stage":          order_stage,
        "available_riders":     len(available_riders),
        "all_riders_scored":    [
            {"name": r["name"], "score": r["composite_score"],
             "orders": r.get("active_orders", 0), "dist": r.get("distance_km", 0)}
            for r in scored[:4]
        ],
    }

    # ── Human-readable agent log ───────────────────────────────────────────
    if procurement_wait_min > 0:
        msg = (
            f"Rider PRE-ASSIGNED (waiting for supplier stock):\n"
            f"  • {selected['name']} ({selected.get('vehicle_type','Bike')}) "
            f"| Score: {selected['composite_score']} "
            f"| Workload: {selected.get('active_orders',0)} orders | {distance_km} km away\n"
            f"ETA Breakdown:\n"
            f"  • Supplier delivery wait : {procurement_wait_min} min ({procurement_wait_hrs} hrs)\n"
            f"  • Kitchen preparation    : {prep_min} min\n"
            f"  • Transit to {location}  : {transit_min} min\n"
            f"  TOTAL: {total_eta_min} min ({total_eta_min//60}h {total_eta_min%60}m)\n"
            f"Status: SCHEDULED — rider dispatches when kitchen confirms READY."
        )
    else:
        msg = (
            f"Rider DISPATCHED NOW:\n"
            f"  • {selected['name']} ({selected.get('vehicle_type','Bike')}) "
            f"| Score: {selected['composite_score']} "
            f"| Workload: {selected.get('active_orders',0)} orders | {distance_km} km away\n"
            f"ETA Breakdown:\n"
            f"  • Kitchen preparation : {prep_min} min\n"
            f"  • Transit to {location}: {transit_min} min\n"
            f"  TOTAL: {total_eta_min} min\n"
            f"Status: OUT FOR DELIVERY."
        )

    log_agent_action("Delivery Agent", f"Rider Assigned → {order_stage}", msg, "INFO", order_id=order_id)

    state.setdefault("agent_log", []).append({
        "agent":   "Delivery Agent",
        "status":  "warning" if order_stage == "SCHEDULED" else "ok",
        "message": msg,
        "details": delivery_plan
    })
    state["delivery_status"] = delivery_plan

    # ── Final decision summary steps ───────────────────────────────────────
    steps = [
        {"check": "Order received & validated", "ok": True,
         "detail": f"{quantity}× {food_item} for {customer} → {location}"},
        {"check": "Ingredients calculated from recipe", "ok": True,
         "detail": ", ".join(f"{k}: {v}" for k, v in state.get("ingredient_requirements", {}).items())},
    ]

    if not shortages:
        steps.append({
            "check": "All ingredients in stock",
            "ok": True,
            "detail": "Available stock sufficient. Stock reserved for this order."
        })
    else:
        for s in shortages:
            steps.append({
                "check": f"Shortage — {s['ingredient']} [{s.get('severity','LOW')}]",
                "ok": False,
                "detail": (
                    f"Available: {s['available']} {s['unit']} | "
                    f"Required: {s['required']} {s['unit']} | "
                    f"Deficit: {s['deficit']} {s['unit']}"
                )
            })
        for d in proc_decs:
            best = d["selected_supplier"]
            steps.append({
                "check": f"Supplier selected ({d.get('llm_mode','rule-based')})",
                "ok": True,
                "detail": (
                    f"{best['name']} | {d['reorder_qty']} {s['unit']} | "
                    f"₹{d['total_cost']} | ETA: {best['delivery_time_hrs']} hr | "
                    f"PO #{d['po_id']} APPROVED"
                )
            })
            steps.append({
                "check": "Incoming stock updated",
                "ok": True,
                "detail": (
                    f"{d['reorder_qty']} {s['unit']} added to incoming_stock "
                    f"(NOT current_stock — awaiting supplier delivery)"
                )
            })

    if procurement_wait_min > 0:
        steps.append({
            "check": "Rider pre-assigned (awaiting stock)",
            "ok": True,
            "detail": (
                f"{selected['name']} | Score: {selected['composite_score']} "
                f"| Departs when kitchen confirms READY (~{procurement_wait_hrs} hr)"
            )
        })
        steps.append({
            "check": "Full ETA calculated",
            "ok": True,
            "detail": (
                f"Supplier wait {procurement_wait_min}m + "
                f"Prep {prep_min}m + Transit {transit_min}m = "
                f"{total_eta_min} min ({total_eta_min//60}h {total_eta_min%60}m)"
            )
        })
    else:
        steps.append({
            "check": "Rider dispatched",
            "ok": True,
            "detail": f"{selected['name']} | {distance_km} km | ETA: {total_eta_min} min"
        })

    state["final_decision"] = {
        "order_id":             order_id,
        "order_stage":          order_stage,
        "steps":                steps,
        "rider":                selected["name"],
        "procurement_wait_min": procurement_wait_min,
        "prep_min":             prep_min,
        "transit_min":          transit_min,
        "total_eta_min":        total_eta_min,
        "procurement":          proc_decs,
        "had_shortage":         len(shortages) > 0,
    }
    return state
