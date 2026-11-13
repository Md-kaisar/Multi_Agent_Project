# FOODFLOW AI
### Agentic AI-Based Food Delivery Supply Chain System

FoodFlow AI is a streamlined, highly demonstrable multi-agent AI food supply chain management system built using **HTML5**, **CSS3**, **Vanilla JavaScript**, **Python Flask REST API**, **Firebase Firestore** (with automatic SQLite fallback), **LangGraph**, and **Gemini API**.

---

## 🌟 Core Demo Concept

> **Customer places order ➔ Order Agent validates ➔ Inventory Agent detects stock deficit ➔ Procurement Agent evaluates vendors & selects Supplier B ➔ Delivery Agent assigns rider ➔ Final Autonomous Decision generated.**

The system operates autonomously—the user doesn't manually decide every step. The AI agents observe, reason, decide, and act across a 5-screen interactive dashboard.

---

## 📱 The 5 Core Screens

1. **Screen 1: Dashboard**: System overview with 4 KPI cards (Orders Today, Pending Orders, Low Stock, AI Actions), real-time **AI Supply Chain Status**, and live **Recent AI Activity** stream.
2. **Screen 2: Create Order**: Input form (`Aritra`, `Chicken Biryani`, `10 Qty`, `New Town`) with a single high-impact action button: `⚡ PROCESS WITH AI`.
3. **Screen 3: AI Agent Pipeline (The Flagship Demo)**: Step-by-step live sequence:
   - **Step 1: 🤖 Order Agent**: Validates Order #1045.
   - **Step 2: 📦 Inventory Agent**: Detects 2.0 kg Chicken stock deficit.
   - **Step 3: 🛒 Procurement Agent**: Evaluates Supplier A (₹220, 3h), Supplier B (₹210, 1h), Supplier C (₹200, 6h). **AI Decision**: Selects Supplier B with Gemini reasoning.
   - **Step 4: 🚚 Delivery Agent**: Assigns Rider #04 (Distance 3.2 km, ETA 25 mins).
4. **Screen 4: 🧠 AI Supply Chain Decision**: Executive summary card displaying final order status, selected supplier, assigned rider, ETA, and Gemini AI reasoning explanation.
5. **Screen 5: Inventory & Suppliers**: Ingredient stock tables with AI reorder recommendations and vendor comparison scorecards.

---

## 🚀 Running the System

```bash
cd /Users/aritralala/.gemini/antigravity/scratch/foodflow-ai
source venv/bin/activate
python app.py
```

Open your web browser at **`http://localhost:5001`**.
