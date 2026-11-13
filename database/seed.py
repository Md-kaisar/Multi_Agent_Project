import os
os.environ["GRPC_DNS_RESOLVER"] = "native"
import random
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore

creds_path = os.path.join(os.path.dirname(__file__), "..", "firebase_credentials.json")
if not os.path.exists(creds_path):
    print(f"ERROR: {creds_path} not found. Cannot seed Firebase.")
    exit(1)

if not firebase_admin._apps:
    cred = credentials.Certificate(creds_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

def wipe_collection(collection_name):
    docs = db.collection(collection_name).limit(100).stream()
    deleted = 0
    for doc in docs:
        doc.reference.delete()
        deleted += 1
    if deleted >= 100:
        wipe_collection(collection_name)

def seed_db():
    print("Wiping existing collections...")
    collections = ['customers', 'products', 'ingredients', 'inventory', 'suppliers', 'delivery_riders', 'orders', 'agent_logs', 'product_ingredients']
    for coll in collections:
        wipe_collection(coll)
    
    print("Seeding customers...")
    customers = [
        {"name": "Aarav Sharma", "phone": "+91-9876543210", "address": "12th Main, Indiranagar, Bengaluru"},
        {"name": "Priya Patel", "phone": "+91-9876543211", "address": "5th Block, Koramangala, Bengaluru"},
        {"name": "Rahul Verma", "phone": "+91-9876543212", "address": "Sector 3, HSR Layout, Bengaluru"},
        {"name": "Ananya Iyer", "phone": "+91-9876543213", "address": "MG Road, Central Bengaluru"},
        {"name": "Rohan Gupta", "phone": "+91-9876543214", "address": "Phase 2, Whitefield, Bengaluru"},
    ]
    for c in customers:
        db.collection('customers').add(c)

    print("Seeding products...")
    products = [
        {"name": "Chicken Biryani", "category": "Main Course", "price": 280.0, "prep_time_mins": 20},
        {"name": "Chicken Roll", "category": "Snacks", "price": 150.0, "prep_time_mins": 12},
        {"name": "Veg Biryani", "category": "Main Course", "price": 220.0, "prep_time_mins": 18},
        {"name": "Paneer Butter Masala", "category": "Main Course", "price": 240.0, "prep_time_mins": 15},
        {"name": "Fried Rice", "category": "Main Course", "price": 180.0, "prep_time_mins": 10},
        {"name": "Chicken Kebab", "category": "Starters", "price": 260.0, "prep_time_mins": 15},
    ]
    for p in products:
        db.collection('products').add(p)

    print("Seeding inventory...")
    inventory = [
        {"ingredient_name": "Chicken", "current_stock": 12.0, "reserved_stock": 0.0, "incoming_stock": 0.0, "min_stock": 25.0, "unit": "kg", "status": "CRITICAL"},
        {"ingredient_name": "Rice", "current_stock": 45.0, "reserved_stock": 0.0, "incoming_stock": 0.0, "min_stock": 30.0, "unit": "kg", "status": "NORMAL"},
        {"ingredient_name": "Paneer", "current_stock": 8.0, "reserved_stock": 0.0, "incoming_stock": 0.0, "min_stock": 15.0, "unit": "kg", "status": "LOW"},
        {"ingredient_name": "Potato", "current_stock": 35.0, "reserved_stock": 0.0, "incoming_stock": 0.0, "min_stock": 20.0, "unit": "kg", "status": "NORMAL"},
        {"ingredient_name": "Onion", "current_stock": 18.0, "reserved_stock": 0.0, "incoming_stock": 0.0, "min_stock": 15.0, "unit": "kg", "status": "NORMAL"},
        {"ingredient_name": "Tomato", "current_stock": 14.0, "reserved_stock": 0.0, "incoming_stock": 0.0, "min_stock": 15.0, "unit": "kg", "status": "LOW"},
        {"ingredient_name": "Oil", "current_stock": 22.0, "reserved_stock": 0.0, "incoming_stock": 0.0, "min_stock": 15.0, "unit": "L", "status": "NORMAL"},
        {"ingredient_name": "Spices", "current_stock": 6.0, "reserved_stock": 0.0, "incoming_stock": 0.0, "min_stock": 10.0, "unit": "kg", "status": "LOW"},
        {"ingredient_name": "Flour", "current_stock": 25.0, "reserved_stock": 0.0, "incoming_stock": 0.0, "min_stock": 15.0, "unit": "kg", "status": "NORMAL"},
        {"ingredient_name": "Vegetables", "current_stock": 20.0, "reserved_stock": 0.0, "incoming_stock": 0.0, "min_stock": 15.0, "unit": "kg", "status": "NORMAL"},
    ]
    for i in inventory:
        db.collection('inventory').add(i)

    print("Seeding suppliers...")
    suppliers = [
        {"name": "Apex Poultry & Fresh Meat", "ingredient_name": "Chicken", "price_per_unit": 220.0, "available_quantity": 100.0, "delivery_time_hrs": 3.0, "reliability_score": 0.90},
        {"name": "Express Farm Direct", "ingredient_name": "Chicken", "price_per_unit": 210.0, "available_quantity": 80.0, "delivery_time_hrs": 1.0, "reliability_score": 0.94},
        {"name": "Budget Wholesale Traders", "ingredient_name": "Chicken", "price_per_unit": 195.0, "available_quantity": 200.0, "delivery_time_hrs": 7.5, "reliability_score": 0.82},
        {"name": "GreenValley Agro Supply", "ingredient_name": "Chicken", "price_per_unit": 235.0, "available_quantity": 50.0, "delivery_time_hrs": 0.5, "reliability_score": 0.98},
        {"name": "Royal Grain Merchants", "ingredient_name": "Rice", "price_per_unit": 60.0, "available_quantity": 500.0, "delivery_time_hrs": 2.0, "reliability_score": 0.95},
        {"name": "Deccan Rice Mills", "ingredient_name": "Rice", "price_per_unit": 55.0, "available_quantity": 300.0, "delivery_time_hrs": 5.0, "reliability_score": 0.88},
        {"name": "Pure Dairy Farms", "ingredient_name": "Paneer", "price_per_unit": 320.0, "available_quantity": 60.0, "delivery_time_hrs": 1.5, "reliability_score": 0.92},
        {"name": "Amrit Dairy Co-op", "ingredient_name": "Paneer", "price_per_unit": 300.0, "available_quantity": 100.0, "delivery_time_hrs": 4.0, "reliability_score": 0.85},
        {"name": "SpiceCraft Traders", "ingredient_name": "Spices", "price_per_unit": 450.0, "available_quantity": 50.0, "delivery_time_hrs": 2.0, "reliability_score": 0.93},
        {"name": "Fresh Harvest Co.", "ingredient_name": "Vegetables", "price_per_unit": 40.0, "available_quantity": 150.0, "delivery_time_hrs": 1.5, "reliability_score": 0.91},
    ]
    for s in suppliers:
        db.collection('suppliers').add(s)

    print("Seeding riders...")
    riders = [
        {"name": "Rahul Kumar", "phone": "+91-9123456780", "vehicle_type": "Bike", "status": "AVAILABLE", "current_location": "Indiranagar", "active_orders": 0, "distance_km": 2.5},
        {"name": "Vikram Singh", "phone": "+91-9123456781", "vehicle_type": "EV Scooter", "status": "AVAILABLE", "current_location": "Koramangala", "active_orders": 1, "distance_km": 4.0},
        {"name": "Deepa Roy", "phone": "+91-9123456782", "vehicle_type": "Bike", "status": "AVAILABLE", "current_location": "HSR Layout", "active_orders": 0, "distance_km": 3.2},
        {"name": "Amit Sharma", "phone": "+91-9123456783", "vehicle_type": "Scooter", "status": "BUSY", "current_location": "MG Road", "active_orders": 2, "distance_km": 5.5},
        {"name": "Neha Joshi", "phone": "+91-9123456784", "vehicle_type": "EV Scooter", "status": "AVAILABLE", "current_location": "Whitefield", "active_orders": 1, "distance_km": 6.1},
        {"name": "Ravi Tiwari", "phone": "+91-9123456785", "vehicle_type": "Bike", "status": "AVAILABLE", "current_location": "Yelahanka", "active_orders": 0, "distance_km": 4.8},
    ]
    for r in riders:
        db.collection('delivery_riders').add(r)

    print("Seeding initial agent logs...")
    now = datetime.now()
    initial_logs = [
        {"timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "agent_name": "Order Agent", "action": "System Startup", "details": "FoodFlow AI initialized.", "status": "INFO", "order_id": None},
        {"timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "agent_name": "Inventory Agent", "action": "Stock Alert", "details": "ALERT: Chicken at 12 kg — below critical threshold (25 kg). Available for new orders: 12 kg.", "status": "WARNING", "order_id": None},
        {"timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "agent_name": "Inventory Agent", "action": "Stock Alert", "details": "ALERT: Paneer at 8 kg — below threshold (15 kg). Available: 8 kg.", "status": "WARNING", "order_id": None},
        {"timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "agent_name": "Procurement Agent", "action": "Supplier Evaluation", "details": "Evaluated 4 Chicken suppliers. GreenValley Agro (Score:0.89) vs Express Farm Direct (Score:0.83).", "status": "INFO", "order_id": None},
        {"timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "agent_name": "Delivery Agent", "action": "Rider Status", "details": "6 riders registered. 4 AVAILABLE, 1 BUSY. Avg distance: 4.2 km.", "status": "INFO", "order_id": None},
    ]
    for log in initial_logs:
        db.collection('agent_logs').add(log)

    print("FoodFlow AI — Firebase seeded successfully.")

if __name__ == "__main__":
    seed_db()
