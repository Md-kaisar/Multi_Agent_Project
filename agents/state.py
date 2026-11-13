from typing import TypedDict, List, Dict, Any, Optional


class AgentState(TypedDict):
    # ── Input (from form) ──────────────────────────────────────────────────
    customer_name:      str
    food_item:          str
    quantity:           int
    delivery_location:  str

    # ── Set by Order Agent ────────────────────────────────────────────────
    order_id:               Optional[int]
    order_priority:         str          # "NORMAL" | "HIGH" | "CRITICAL"
    total_order_value:      float
    ingredient_requirements: Dict[str, float]   # {"Chicken": 5.0, ...}

    # ── Set by Inventory Agent ────────────────────────────────────────────
    inventory_snapshot:  List[Dict[str, Any]]   # full DB snapshot
    shortages:           List[Dict[str, Any]]   # detailed per-ingredient
    # shortage schema: {ingredient, required, available, deficit, unit, severity}
    needs_procurement:   bool

    needs_escalation:    bool

    # ── Set by Procurement Agent (only if needs_procurement=True) ─────────
    procurement_decision:   Optional[Dict[str, Any]]
    # procurement_decision schema:
    #   status: "COMPLETED" | "NOT_REQUIRED"
    #   decisions: [{ ingredient, deficit, selected_supplier, all_suppliers,
    #                 po_id, total_cost, supplier_delivery_hrs }]
    #   total_wait_hrs: float  ← max supplier delivery time across all POs
    #   total_procurement_cost: float

    # ── Set by Delivery Agent ─────────────────────────────────────────────
    delivery_status:    Optional[Dict[str, Any]]
    # delivery_status schema:
    #   rider_name, vehicle, distance_km, prep_min, transit_min, eta_min,
    #   procurement_wait_min, total_eta_min, order_stage

    # ── Running log (all agents append here) ──────────────────────────────
    agent_log:          List[Dict[str, Any]]

    # ── Final compiled decision (set by Delivery Agent) ───────────────────
    final_decision:     Optional[Dict[str, Any]]
