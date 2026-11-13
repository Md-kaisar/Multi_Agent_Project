"""
Order Agent
-----------
OBSERVE : Receives customer order (food item + quantity + location)
REASON  : Calculates required ingredient quantities from the recipe DB
          Determines order priority based on quantity
ACT     : Creates order record in DB with correct status + priority
PASS    : ingredient_requirements → Inventory Agent
"""

from agents.state import AgentState
from database.database import (
    log_agent_action, get_customer_by_name, create_customer,
    get_product_by_name, create_order
)

# ─── Recipe: kg (or L for Oil) per single portion ───────────────────────────
RECIPES = {
    "Chicken Biryani":      {"Chicken": 0.50, "Rice": 0.25, "Oil": 0.05, "Spices": 0.03},
    "Chicken Roll":         {"Chicken": 0.30, "Flour": 0.10, "Oil": 0.02},
    "Veg Biryani":          {"Rice": 0.25, "Vegetables": 0.20, "Oil": 0.05, "Spices": 0.02},
    "Paneer Butter Masala": {"Paneer": 0.25, "Tomato": 0.15, "Oil": 0.05, "Spices": 0.03},
}
DEFAULT_RECIPE = {"Chicken": 0.40, "Rice": 0.20, "Oil": 0.04}

# ─── Priority thresholds ─────────────────────────────────────────────────────
def _order_priority(qty: int) -> str:
    if qty >= 50:
        return "CRITICAL"
    if qty >= 20:
        return "HIGH"
    return "NORMAL"


def run_order_agent(state: AgentState) -> AgentState:
    food_item = state["food_item"]
    quantity  = state["quantity"]
    cust_name = state["customer_name"]
    location  = state["delivery_location"]
    priority  = _order_priority(quantity)

    # 1. Calculate ingredient requirements from recipe
    recipe       = RECIPES.get(food_item, DEFAULT_RECIPE)
    requirements = {ing: round(per_portion * quantity, 3)
                    for ing, per_portion in recipe.items()}

    # 2. Resolve / create customer record
    cust = get_customer_by_name(cust_name)
    if cust:
        cust_id = cust["id"]
    else:
        cust_id = create_customer(cust_name, "+91-0000000000", location)

    # 3. Resolve product record
    prod = get_product_by_name(food_item)
    if prod:
        prod_id = prod["id"]
        price   = prod["price"]
    else:
        prod_id, price = "fallback_prod_id", 250.0

    total_value = price * quantity

    # 4. Create order in DB — status starts as PENDING (not yet confirmed by inventory)
    order_id = create_order(cust_id, prod_id, quantity, location, total_value, priority)

    # 5. Log and annotate
    req_summary = ", ".join(
        f"{ing}: {qty} {'L' if ing == 'Oil' else 'kg'}"
        for ing, qty in requirements.items()
    )
    msg = (
        f"Order #{order_id} received | Priority: {priority}\n"
        f"Customer: {cust_name} | Location: {location}\n"
        f"Item: {quantity}× {food_item} | Total: ₹{total_value:.2f}\n"
        f"Ingredients required: {req_summary}"
    )
    log_agent_action("Order Agent", "Order Received & Ingredient Mapping", msg, "INFO")

    log = state.get("agent_log", [])
    log.append({
        "agent":   "Order Agent",
        "status":  "ok",
        "message": msg,
        "details": {
            "order_id":         order_id,
            "priority":         priority,
            "quantity":         quantity,
            "food_item":        food_item,
            "total_value":      total_value,
            "requirements":     requirements
        }
    })

    state["order_id"]               = order_id
    state["order_priority"]         = priority
    state["total_order_value"]      = total_value
    state["ingredient_requirements"]= requirements
    state["agent_log"]              = log
    return state
