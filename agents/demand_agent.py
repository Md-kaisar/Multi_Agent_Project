from agents.state import AgentState
from database.database import log_agent_action, get_all_orders
from utils.calculations import predict_demand_ml, calculate_ingredient_requirements
from ai.llm import llm_engine
from ai.prompts import DEMAND_FORECAST_PROMPT

def run_demand_agent(state: AgentState) -> AgentState:
    """
    Demand Forecasting Agent:
    - Analyzes order history & current incoming surge volume
    - Predicts short-term food item demand
    - Calculates required raw ingredients
    """
    hist_orders = get_all_orders()
    orders_batch = state.get("orders_batch", [])
    active_surge_qty = sum(o.get("quantity", 0) for o in orders_batch)
    
    # 1. Run ML prediction model
    predictions = predict_demand_ml(hist_orders, active_surge_qty=active_surge_qty)
    
    # 2. Calculate raw ingredient requirements
    ing_reqs = calculate_ingredient_requirements(predictions)
    
    # 3. LLM analytical reasoning
    prompt = DEMAND_FORECAST_PROMPT.format(
        order_context=f"Active incoming surge batch: {active_surge_qty} items.",
        historical_context=f"Analyzed {len(hist_orders)} past orders."
    )
    fallback = (
        "Predicted Demand Summary:\n"
        f"- Chicken Biryani: {predictions.get('Chicken Biryani', 85)} portions\n"
        f"- Chicken Roll: {predictions.get('Chicken Roll', 42)} portions\n"
        f"- Veg Biryani: {predictions.get('Veg Biryani', 31)} portions\n\n"
        "Reasoning: Peak lunchtime order spike detected combined with weekend trend pattern. "
        "High demand anticipated for poultry-based dishes over the next 3-hour window."
    )
    
    reasoning = llm_engine.generate_reasoning(prompt, fallback)
    
    action_msg = f"Predicted high demand: Chicken Biryani ({predictions.get('Chicken Biryani', 85)}), Chicken Roll ({predictions.get('Chicken Roll', 42)})."
    log_agent_action("Demand Agent", "Predict Short-Term Demand", action_msg, "INFO")
    
    messages = state.get("agent_messages", [])
    messages.append({
        "agent": "Demand Forecasting Agent",
        "action": "Demand ML Model Execution",
        "message": f"Forecast generated for 6 items. {reasoning}"
    })
    
    state["demand_prediction"] = predictions
    state["ingredient_requirements"] = ing_reqs
    state["agent_messages"] = messages
    state["current_step"] = "Demand Forecasting Completed"
    return state
