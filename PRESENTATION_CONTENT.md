# PRESENTATION CONTENT: FoodFlow AI
## B.Tech Mini-Project Presentation Deck (12 Slides)

---

### SLIDE 1: Title Slide
**Title**: FoodFlow AI – An Agentic AI-Based Food Delivery Supply Chain Management System
**Subtitle**: Autonomous Multi-Agent Orchestration from Procurement to Doorstep Delivery
**Presenter**: B.Tech Computer Science & Engineering Candidate
**Tech Stack**: LangGraph, LangChain, Python, Streamlit, SQLite, Gemini/OpenAI

---

### SLIDE 2: Problem Statement
- **Food Delivery Bottlenecks**: Sudden order surges deplete raw material stock unexpectedly.
- **Siloed Operations**: Kitchen, procurement, and delivery logistics act independently without real-time coordination.
- **Flawed Procurement**: Traditional buyers select suppliers strictly on unit price, leading to catastrophic 7+ hour delivery lead-time delays during rush hours.
- **Lack of Autonomy**: Standard ERP systems require constant manual human supervision.

---

### SLIDE 3: Motivation & Vision
- **Why Agentic AI?**: Traditional scripts follow fixed rules; AI Agents observe, analyze, reason, plan, act, and verify autonomously.
- **Vision**: Create an end-to-end self-healing food delivery supply chain that automatically detects inventory shortages, procures ingredients, optimizes kitchen preparation, and dispatches riders.

---

### SLIDE 4: Proposed Solution - FoodFlow AI
- **Multi-Agent Architecture**: Built on **LangGraph** with a shared state pipeline.
- **6 Autonomous Agents**: Order Agent ➔ Demand Forecasting Agent ➔ Inventory Agent ➔ Procurement Agent ➔ Kitchen Agent ➔ Delivery Agent.
- **Multi-Criteria Vendor Evaluation**: Balanced weighted formula prioritizing delivery speed during demand surges.
- **Resilient AI Engine**: Operates with Gemini API / OpenAI API, with a zero-crash deterministic fallback for offline demos.

---

### SLIDE 5: System Architecture
```
+-------------------------------------------------------------+
|                     Streamlit Dashboard UI                  |
+-------------------------------------------------------------+
                              │
                              ▼
+-------------------------------------------------------------+
|              LangGraph State Graph Execution Engine          |
|  Order ➔ Demand ML ➔ Inventory Alert ➔ Procurement ➔ Delivery|
+-------------------------------------------------------------+
                              │
                              ▼
+-------------------------------------------------------------+
|                    SQLite Database Layer                    |
|      (Orders, Inventory, Suppliers, Purchase Orders, Logs)   |
+-------------------------------------------------------------+
```

---

### SLIDE 6: Multi-Agent Roles & Responsibilities
- 🤖 **Order Agent**: Validates incoming orders and breaks down portion ingredient usage.
- 📈 **Demand Agent**: Predicts short-term dish demand using scikit-learn regression models.
- 📦 **Inventory Agent**: Compares stock levels against demand and flags stock-out risks.
- 🛒 **Procurement Agent**: Ranks candidate suppliers and issues purchase orders.
- 🍳 **Kitchen Agent**: Optimizes prep batching and cook schedules.
- 🛵 **Delivery Agent**: Calculates distance/traffic matrix, assigns riders, and tracks ETAs.

---

### SLIDE 7: Autonomous Workflow (Observe ➔ Act)
1. **Observe**: Order Agent detects 25 incoming Chicken Biryani orders.
2. **Analyze**: Demand Agent predicts demand spike of 85 portions.
3. **Reason**: Inventory Agent detects 20 kg Chicken deficit.
4. **Plan**: Procurement Agent compares 4 suppliers and selects *Express Farm Direct* (1-hour lead time).
5. **Act**: System issues PO, updates stock, schedules 18-min kitchen prep, and dispatches rider.
6. **Verify**: Chief AI Officer synthesizes final executive optimization report.

---

### SLIDE 8: Dynamic Supplier Decision Formula
- Procurement Agent uses a weighted composite scoring formula:
  $$\text{Score} = (0.45 \times \text{Speed Score}) + (0.35 \times \text{Reliability}) + (0.20 \times \text{Price Economy})$$
- **Result**: Selects fast 1-hour vendor (₹210/kg) over 7.5-hour cheap vendor (₹195/kg) to eliminate kitchen stockout downtime.

---

### SLIDE 9: Technology Stack
- **Frontend**: Streamlit, Custom CSS, Plotly
- **Agent Orchestration**: LangGraph, LangChain
- **Backend & Database**: Python 3.10+, SQLite
- **Machine Learning**: Scikit-Learn, Pandas
- **LLM Reasoning**: Google Gemini API (`gemini-1.5-flash`) with Deterministic Fallback Mode

---

### SLIDE 10: Demo & Key Screenshots
- **1-Click Simulation**: "🚀 RUN AUTONOMOUS SUPPLY CHAIN" button executes all 6 agents live.
- **Interactive UI**: Real-time KPI metric cards, stock gauge charts, and expander event logs.
- **Full Audit Trail**: Every agent step is recorded in SQLite `agent_logs`.

---

### SLIDE 11: Advantages & Business Impact
- **Zero Human Intervention**: Completely automates emergency procurement during rush hours.
- **Reduced Downtime**: Prevents food order cancellations caused by missing raw ingredients.
- **100% Local Runnable Setup**: Requires minimal dependencies and no complex cloud deployment.

---

### SLIDE 12: Conclusion & Future Scope
- **Conclusion**: FoodFlow AI proves that multi-agent AI systems can autonomously solve complex, fast-moving supply chain disruptions.
- **Future Scope**: Integrate Google Maps API for live GPS rider routing and incorporate weather APIs for predictive demand modeling.
- **Thank You!** Questions & Answers.
