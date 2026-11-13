"""
database.py — FoodFlow AI Data Layer (Firebase Firestore)
All DB operations go through this module.
"""

import os
os.environ["GRPC_DNS_RESOLVER"] = "native"
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
creds_path = os.getenv("FIREBASE_CREDENTIALS", "firebase_credentials.json")
db = None
if os.path.exists(creds_path):
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(creds_path)
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Connected to Firebase Firestore successfully!")
    except Exception as e:
        print(f"Failed to connect to Firebase Firestore: {e}")
else:
    print(f"Warning: {creds_path} not found. Firebase will not work.")

def _get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ─── Agent Logs ──────────────────────────────────────────────────────────────

def log_agent_action(agent_name, action, details, status="INFO", order_id=None):
    if not db: return
    db.collection('agent_logs').add({
        "timestamp": _get_timestamp(),
        "agent_name": agent_name,
        "action": action,
        "details": str(details),
        "status": status,
        "order_id": order_id
    })

def get_agent_logs(limit=20):
    if not db: return []
    docs = db.collection('agent_logs').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit).stream()
    logs = []
    for doc in docs:
        d = doc.to_dict()
        d['id'] = doc.id
        logs.append(d)
    return logs

# ─── KPIs ────────────────────────────────────────────────────────────────────

def get_kpis():
    if not db: return {}
    orders_count = len(list(db.collection('orders').stream()))
    
    # Low stock calculation
    inv_docs = db.collection('inventory').stream()
    low_stock = sum(1 for doc in inv_docs if (doc.to_dict().get('current_stock', 0) - doc.to_dict().get('reserved_stock', 0)) < doc.to_dict().get('min_stock', 0))
    
    pending = len(list(db.collection('orders').where('status', 'in', ['PENDING','AWAITING_PROCUREMENT','PROCUREMENT_ORDERED','SCHEDULED']).stream()))
    
    logs = list(db.collection('agent_logs').stream())
    ai_actions = len(logs)
    actions_breakdown = {}
    for log in logs:
        d = log.to_dict()
        name = d.get('agent_name', 'System')
        actions_breakdown[name] = actions_breakdown.get(name, 0) + 1
        
    total_suppliers = len(list(db.collection('suppliers').stream()))
    
    return {
        "orders_today": orders_count,
        "pending_orders": pending,
        "inventory_alerts": low_stock,
        "agent_actions": ai_actions,
        "agent_breakdown": actions_breakdown,
        "suppliers": total_suppliers,
    }

# ─── Products / Customers ────────────────────────────────────────────────────

def get_products():
    if not db: return []
    return [doc.to_dict() | {'id': doc.id} for doc in db.collection('products').stream()]

def get_product_by_name(name):
    if not db: return None
    docs = list(db.collection('products').where('name', '==', name).stream())
    if docs:
        return docs[0].to_dict() | {'id': docs[0].id}
    return None

def get_customers():
    if not db: return []
    return [doc.to_dict() | {'id': doc.id} for doc in db.collection('customers').stream()]

def get_customer_by_name(name):
    if not db: return None
    docs = list(db.collection('customers').where('name', '==', name).stream())
    if docs:
        return docs[0].to_dict() | {'id': docs[0].id}
    return None

def create_customer(name, phone, address):
    if not db: return None
    _, doc_ref = db.collection('customers').add({
        "name": name,
        "phone": phone,
        "address": address
    })
    return doc_ref.id

# ─── Inventory ───────────────────────────────────────────────────────────────

def get_inventory_details():
    if not db: return []
    docs = db.collection('inventory').stream()
    items = []
    for doc in docs:
        d = doc.to_dict()
        d['id'] = doc.id
        d['available_stock'] = round(d.get('current_stock', 0) - d.get('reserved_stock', 0), 3)
        items.append(d)
    items.sort(key=lambda x: (0 if x['available_stock'] < x.get('min_stock', 0) else 1, x.get('ingredient_name', '')))
    return items

def get_inventory_by_ingredient(ingredient_name):
    if not db: return None
    docs = list(db.collection('inventory').where('ingredient_name', '==', ingredient_name).stream())
    if docs:
        d = docs[0].to_dict()
        d['id'] = docs[0].id
        d['available_stock'] = round(d.get('current_stock', 0) - d.get('reserved_stock', 0), 3)
        return d
    return None

def reserve_stock(ingredient_name: str, qty: float) -> bool:
    if not db: return False
    inv = get_inventory_by_ingredient(ingredient_name)
    if not inv: return False
    doc_ref = db.collection('inventory').document(inv['id'])
    doc_ref.update({
        "reserved_stock": firestore.Increment(round(qty, 3)),
        "last_updated": _get_timestamp()
    })
    return True

def add_incoming_stock(ingredient_name: str, qty: float) -> bool:
    if not db: return False
    inv = get_inventory_by_ingredient(ingredient_name)
    if not inv: return False
    doc_ref = db.collection('inventory').document(inv['id'])
    doc_ref.update({
        "incoming_stock": firestore.Increment(round(qty, 3)),
        "last_updated": _get_timestamp()
    })
    return True

def receive_incoming_stock(ingredient_name: str) -> bool:
    if not db: return False
    inv = get_inventory_by_ingredient(ingredient_name)
    if not inv: return False
    
    current = inv.get("current_stock", 0.0)
    incoming = inv.get("incoming_stock", 0.0)
    min_stock = inv.get("min_stock", 0.0)
    
    new_current = round(current + incoming, 3)
    new_status = "NORMAL" if new_current >= min_stock else "LOW"
    
    db.collection('inventory').document(inv['id']).update({
        "current_stock": new_current,
        "incoming_stock": 0.0,
        "status": new_status,
        "last_updated": _get_timestamp()
    })
    return True

def update_inventory_stock(ingredient_name: str, delta: float) -> bool:
    if not db: return False
    inv = get_inventory_by_ingredient(ingredient_name)
    if not inv: return False
    
    current = inv.get("current_stock", 0.0)
    min_stock = inv.get("min_stock", 0.0)
    
    new_stock = max(0.0, round(current + delta, 3))
    new_status = "NORMAL" if new_stock >= min_stock else "LOW"
    
    db.collection('inventory').document(inv['id']).update({
        "current_stock": new_stock,
        "status": new_status,
        "last_updated": _get_timestamp()
    })
    return True

# ─── Suppliers ───────────────────────────────────────────────────────────────

def get_suppliers_for_ingredient(ingredient_name=None):
    if not db: return []
    query = db.collection('suppliers')
    if ingredient_name:
        query = query.where('ingredient_name', '==', ingredient_name)
    docs = query.stream()
    sups = [doc.to_dict() | {'id': doc.id} for doc in docs]
    if ingredient_name:
        sups.sort(key=lambda x: x.get('reliability_score', 0), reverse=True)
    else:
        sups.sort(key=lambda x: x.get('name', ''))
    return sups

def get_suppliers():
    return get_suppliers_for_ingredient()

# ─── Orders & Delivery ───────────────────────────────────────────────────────

def create_order(customer_id, product_id, quantity, delivery_location, total_amount, priority="NORMAL"):
    if not db: return None
    _, doc_ref = db.collection('orders').add({
        "customer_id": customer_id,
        "product_id": product_id,
        "quantity": quantity,
        "total_amount": total_amount,
        "delivery_location": delivery_location,
        "status": "PENDING",
        "priority": priority,
        "created_at": _get_timestamp()
    })
    return doc_ref.id

def update_order_status(order_id, status):
    if not db: return
    db.collection('orders').document(order_id).update({"status": status})

def get_all_orders():
    if not db: return []
    docs = db.collection('orders').order_by('created_at', direction=firestore.Query.DESCENDING).stream()
    orders = []
    
    for doc in docs:
        o = doc.to_dict()
        o['id'] = doc.id
        
        # Resolve customer and product names
        cust = db.collection('customers').document(o.get('customer_id')).get() if o.get('customer_id') else None
        prod = db.collection('products').document(o.get('product_id')).get() if o.get('product_id') else None
        o['customer_name'] = cust.to_dict().get('name', 'Unknown') if cust and cust.exists else 'Unknown'
        o['product_name'] = prod.to_dict().get('name', 'Unknown') if prod and prod.exists else 'Unknown'

        st = (o.get("status") or "").upper()
        if st in ("DELIVERED", "OUT_FOR_DELIVERY", "COMPLETED"):
            o["ai_status"] = "✓ Completed"
        elif st in ("PROCUREMENT_ORDERED", "AWAITING_PROCUREMENT", "SCHEDULED"):
            o["ai_status"] = "⏳ Scheduled"
        elif st in ("PROCESSING", "PREPARING", "CONFIRMED", "READY_FOR_DELIVERY"):
            o["ai_status"] = "⚙ Processing"
        elif st == "FAILED":
            o["ai_status"] = "❌ Failed"
        elif st == "DELAYED":
            o["ai_status"] = "⚠ Delayed"
        else:
            o["ai_status"] = "🧠 Pending"
        orders.append(o)
    return orders

def create_purchase_order(supplier_id, ingredient_name, quantity, total_cost, recommended_by):
    if not db: return None
    _, doc_ref = db.collection('purchase_orders').add({
        "supplier_id": supplier_id,
        "ingredient_name": ingredient_name,
        "quantity": quantity,
        "total_cost": total_cost,
        "status": "ORDERED",
        "recommended_by_agent": recommended_by,
        "created_at": _get_timestamp()
    })
    return doc_ref.id

def get_delivery_riders():
    if not db: return []
    docs = db.collection('delivery_riders').stream()
    return [doc.to_dict() | {'id': doc.id} for doc in docs]

def create_delivery_assignment(order_id, rider_id, delivery_eta_min, status):
    if not db: return None
    _, doc_ref = db.collection('deliveries').add({
        "order_id": order_id,
        "rider_id": rider_id,
        "delivery_eta_min": delivery_eta_min,
        "status": status,
        "created_at": _get_timestamp()
    })
    return doc_ref.id

def update_rider_status(rider_id, status, active_orders_increment=1):
    if not db: return
    db.collection('delivery_riders').document(rider_id).update({
        "status": status,
        "active_orders": firestore.Increment(active_orders_increment)
    })