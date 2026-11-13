from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os

# ─── DB bootstrap ────────────────────────────────────────────────────────────
# Note: Seed Firebase manually via `python database/seed.py`

# ─── Imports ─────────────────────────────────────────────────────────────────
from database.database import (
    get_kpis, get_products, get_customers, get_all_orders,
    get_inventory_details, get_suppliers, get_agent_logs
)
from agents.graph import run_order_workflow
from ai.llm import llm_engine

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

PROCESSING_LOCKS = set()



# ─── Pages ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ─── KPIs ────────────────────────────────────────────────────────────────────

@app.route("/api/kpis")
def api_kpis():
    kpis = get_kpis()
    kpis["provider"] = "🟢 GEMINI AI ONLINE" if "API" in llm_engine.provider else "🟡 DEMO AI MODE"
    return jsonify(kpis)


# ─── Products / Customers ────────────────────────────────────────────────────

@app.route("/api/products")
def api_products():
    return jsonify(get_products())


@app.route("/api/customers")
def api_customers():
    return jsonify(get_customers())


# ─── Orders ──────────────────────────────────────────────────────────────────

@app.route("/api/orders", methods=["GET"])
def api_orders():
    orders = get_all_orders()
    for o in orders:
        status = (o.get("status") or "").upper()
        if status in ("DELIVERED", "OUT FOR DELIVERY", "COMPLETED"):
            o["ai_status"] = "✓ Completed"
        elif status in ("PROCESSING", "PREPARING"):
            o["ai_status"] = "⚙ Processing"
        else:
            o["ai_status"] = "🧠 Pending"
    return jsonify(orders)


# ─── Inventory ───────────────────────────────────────────────────────────────

@app.route("/api/inventory")
def api_inventory():
    return jsonify(get_inventory_details())


# ─── Suppliers ───────────────────────────────────────────────────────────────

@app.route("/api/suppliers")
def api_suppliers():
    return jsonify(get_suppliers())


# ─── 🔥 CORE AGENTIC ENDPOINT ────────────────────────────────────────────────
# Receives order from form, runs the full 4-agent LangGraph workflow,
# returns the full agent decision trace to the frontend.

@app.route("/api/process-order", methods=["POST"])
def api_process_order():
    data      = request.json or {}
    cust_name = data.get("customer_name", "Aritra")
    food_item = data.get("food_item", "Chicken Biryani")
    quantity  = int(data.get("quantity", 10))
    location  = data.get("delivery_location", "New Town")

    # Flaw #20: Idempotency guard
    lock_key = (cust_name, food_item, quantity, location)
    if lock_key in PROCESSING_LOCKS:
        return jsonify({
            "status": "error",
            "message": "This exact order is already processing or was recently processed. Please wait."
        }), 429
    
    PROCESSING_LOCKS.add(lock_key)

    try:
        final_state = run_order_workflow(cust_name, food_item, quantity, location)

        # Convert to JSON-safe structure
        agent_log        = final_state.get("agent_log", [])
        final_decision   = final_state.get("final_decision", {}) or {}
        delivery         = final_state.get("delivery_status", {}) or {}
        shortages        = final_state.get("shortages", [])
        proc             = final_state.get("procurement_decision") or {}
        requirements     = final_state.get("ingredient_requirements", {})

        return jsonify({
            "status":                  "success",
            "order_id":                final_state.get("order_id"),
            "order_priority":          final_state.get("order_priority", "NORMAL"),
            "total_order_value":       final_state.get("total_order_value", 0.0),
            "agent_log":               agent_log,
            "shortages":               shortages,
            "ingredient_requirements": requirements,
            "needs_procurement":       final_state.get("needs_procurement", False),
            "procurement":             proc,
            "delivery":                delivery,
            "final_decision":          final_decision,
            # Convenience flags for frontend rendering
            "had_shortage":            len(shortages) > 0,
            "order_stage":             delivery.get("order_stage", "OUT_FOR_DELIVERY"),
            "total_eta_min":           delivery.get("total_eta_min", 0),
            "procurement_wait_min":    delivery.get("procurement_wait_min", 0),
        })

    except Exception as exc:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        if lock_key in PROCESSING_LOCKS:
            PROCESSING_LOCKS.remove(lock_key)


# ─── Agent Logs ──────────────────────────────────────────────────────────────

@app.route("/api/logs")
def api_logs():
    return jsonify(get_agent_logs())


# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 FoodFlow AI — http://localhost:5001")
    app.run(host="0.0.0.0", port=5001, debug=True)
