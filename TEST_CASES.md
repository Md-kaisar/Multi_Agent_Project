# TEST CASES: FoodFlow AI

| Test ID | Test Scenario | Input / Action | Expected Result | Pass / Fail |
|:---|:---|:---|:---|:---:|
| **TC01** | Create Valid Customer Order | Submit order form with valid Customer, Product (Chicken Biryani), Qty=2, Location="Indiranagar". | Order is inserted into SQLite `orders` table; success message displayed. | **PASS** |
| **TC02** | Zero Quantity Order Validation | Attempt order submission with Quantity = 0. | Input validation prevents form submission; minimum quantity enforced to 1. | **PASS** |
| **TC03** | Low Inventory Detection | Trigger Inventory Agent when Chicken stock < min_stock threshold. | Inventory Agent flags stock status as CRITICAL and generates stockout alert. | **PASS** |
| **TC04** | Multi-Supplier Trade-Off Analysis | Execute Procurement Agent with 4 suppliers (varying price, lead time, reliability). | Procurement Agent ranks suppliers via composite score and selects optimal vendor (*Express Farm Direct*). | **PASS** |
| **TC05** | Purchase Order Generation & Stock Refill | Execute Procurement Agent purchase order creation. | Purchase Order recorded in DB `purchase_orders`; inventory stock automatically incremented. | **PASS** |
| **TC06** | Missing API Key Fallback Execution | Run simulation without `GEMINI_API_KEY` set in `.env`. | System detects missing key and executes deterministic fallback AI engine without crashing. | **PASS** |
| **TC07** | 1-Click Autonomous Supply Chain Simulation | Click "🚀 RUN AUTONOMOUS SUPPLY CHAIN" button on Simulation page. | All 6 agents (Order ➔ Demand ➔ Inventory ➔ Procurement ➔ Kitchen ➔ Delivery) execute in sequence. | **PASS** |
| **TC08** | Kitchen Batch Cooking Schedule | Pass validated order batch to Kitchen Agent. | Kitchen Agent creates prep batching schedule and estimates cook completion time (18 mins). | **PASS** |
| **TC09** | Delivery Rider Matching & ETA | Execute Delivery Agent with ready order and available riders. | Delivery Agent matches nearest rider (*Rahul Kumar*), calculates traffic ETA (24 mins), and logs dispatch in DB. | **PASS** |
| **TC10** | System Event Audit Logging | Inspect System Logs page after running multi-agent workflow. | All agent actions are recorded in SQLite `agent_logs` with timestamps and log levels. | **PASS** |
