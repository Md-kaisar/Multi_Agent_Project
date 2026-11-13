"""
LangGraph Multi-Agent Supply Chain Workflow
-------------------------------------------
Graph: Order Agent → Inventory Agent → [Procurement Agent?] → Delivery Agent

The conditional edge after Inventory Agent checks state["needs_procurement"]
to decide whether to route through Procurement Agent or skip to Delivery.
"""

from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.order_agent       import run_order_agent
from agents.inventory_agent   import run_inventory_agent
from agents.procurement_agent import run_procurement_agent
from agents.delivery_agent    import run_delivery_agent


def route_after_inventory(state: AgentState) -> str:
    """Conditional router: does the order need procurement?"""
    if state.get("needs_procurement", False):
        return "procurement_agent"
    return "delivery_agent"

def route_after_procurement(state: AgentState) -> str:
    """Conditional router: did procurement fail?"""
    if state.get("needs_escalation", False):
        return END
    return "delivery_agent"


def build_workflow():
    wf = StateGraph(AgentState)

    wf.add_node("order_agent",       run_order_agent)
    wf.add_node("inventory_agent",   run_inventory_agent)
    wf.add_node("procurement_agent", run_procurement_agent)
    wf.add_node("delivery_agent",    run_delivery_agent)

    wf.set_entry_point("order_agent")

    wf.add_edge("order_agent", "inventory_agent")

    # Conditional branch after inventory check
    wf.add_conditional_edges(
        "inventory_agent",
        route_after_inventory,
        {
            "procurement_agent": "procurement_agent",
            "delivery_agent":    "delivery_agent",
        }
    )

    wf.add_conditional_edges(
        "procurement_agent",
        route_after_procurement,
        {
            "delivery_agent": "delivery_agent",
            END: END,
        }
    )
    wf.add_edge("delivery_agent", END)

    return wf.compile()


supply_chain_app = build_workflow()


def run_order_workflow(customer_name: str, food_item: str, quantity: int, delivery_location: str) -> dict:
    """
    Entry point for the Flask API.
    Initialises the AgentState and runs the full LangGraph workflow.
    Returns the final state as a plain dict.
    """
    initial_state: AgentState = {
        "customer_name":           customer_name,
        "food_item":               food_item,
        "quantity":                quantity,
        "delivery_location":       delivery_location,
        "order_id":                None,
        "order_priority":          "NORMAL",
        "total_order_value":       0.0,
        "ingredient_requirements": {},
        "inventory_snapshot":      [],
        "shortages":               [],
        "needs_procurement":       False,
        "needs_escalation":        False,
        "procurement_decision":    None,
        "delivery_status":         None,
        "agent_log":               [],
        "final_decision":          None,
    }


    final = supply_chain_app.invoke(initial_state)
    return dict(final)
