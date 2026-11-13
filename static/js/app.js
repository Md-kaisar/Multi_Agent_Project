/* ═══════════════════════════════════════════════════════════════
   FoodFlow AI — Agentic Supply Chain Client Engine
   ═══════════════════════════════════════════════════════════════ */

// ─── Recipe Map (mirrors backend) ───────────────────────────────
const RECIPES = {
    "Chicken Biryani":      { "Chicken": 0.50, "Rice": 0.25, "Oil": 0.05 },
    "Chicken Roll":         { "Chicken": 0.30, "Flour": 0.10, "Oil": 0.02 },
    "Veg Biryani":          { "Rice": 0.25, "Vegetables": 0.20, "Oil": 0.05 },
    "Paneer Butter Masala": { "Paneer": 0.25, "Tomato": 0.15, "Oil": 0.05 },
};

// ─── Tab Routing ────────────────────────────────────────────────
function switchTab(id, el) {
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelectorAll('.page-view').forEach(v => v.classList.add('hidden'));
    if (el) el.classList.add('active');
    const pg = document.getElementById(`page-${id}`);
    if (pg) pg.classList.remove('hidden');

    if (id === 'dashboard')    loadDashboard();
    if (id === 'inventory')    loadInventory();
    if (id === 'suppliers')    loadSuppliers();
    if (id === 'orders')       loadOrders();
    if (id === 'create-order') updateIngredientPreview();
}

// ─── Boot ───────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    liveClock();
    loadDashboard();
    loadEngineMode();
    loadProductsIntoForm();
    updateIngredientPreview();

    // Ingredient preview updates on change
    document.getElementById('f-food')?.addEventListener('change', updateIngredientPreview);
    document.getElementById('f-qty')?.addEventListener('input',  updateIngredientPreview);
});

function liveClock() {
    const el = document.getElementById('live-clock');
    if (!el) return;
    setInterval(() => { el.innerText = new Date().toLocaleTimeString(); }, 1000);
}

// ─── Toast ──────────────────────────────────────────────────────
function toast(msg, type = 'success') {
    const c = document.getElementById('toast-container');
    const t = document.createElement('div');
    t.className = 'toast';
    t.style.borderLeftColor = type === 'error' ? 'var(--danger)' : type === 'warn' ? 'var(--warning)' : 'var(--success)';
    t.innerHTML = `<span>${type === 'error' ? '❌' : type === 'warn' ? '⚠️' : '✅'}</span> <span>${msg}</span>`;
    c.appendChild(t);
    setTimeout(() => { t.style.opacity = '0'; t.style.transform = 'translateX(50px)'; setTimeout(() => t.remove(), 350); }, 3500);
}

// ─── Ingredient Preview ─────────────────────────────────────────
function updateIngredientPreview() {
    const food = document.getElementById('f-food')?.value || 'Chicken Biryani';
    const qty  = parseInt(document.getElementById('f-qty')?.value || '10');
    const recipe = RECIPES[food] || {};
    const el = document.getElementById('ingredient-list');
    if (!el) return;

    if (!Object.keys(recipe).length) {
        el.innerHTML = '<span style="color:var(--text-muted)">No recipe data.</span>';
        return;
    }
    el.innerHTML = Object.entries(recipe)
        .map(([ing, perPortion]) => {
            const total = (perPortion * qty).toFixed(2);
            const unit  = ing === 'Oil' ? 'L' : 'kg';
            return `• ${ing}: <b style="color:var(--primary)">${total} ${unit}</b> (${perPortion} ${unit} × ${qty})`;
        }).join('<br>');
}

// ─── Load Products into Dropdown ───────────────────────────────
async function loadProductsIntoForm() {
    try {
        const res  = await fetch('/api/products');
        const data = await res.json();
        const sel  = document.getElementById('f-food');
        if (!sel || !data.length) return;
        sel.innerHTML = data.map(p =>
            `<option value="${p.name}">${p.name}</option>`
        ).join('');
        // Keep Chicken Biryani selected by default
        sel.value = 'Chicken Biryani';
        updateIngredientPreview();
    } catch(e) { /* silently use hardcoded options */ }
}

// ─── Engine Mode ────────────────────────────────────────────────
async function loadEngineMode() {
    try {
        const res  = await fetch('/api/kpis');
        const data = await res.json();
        const el   = document.getElementById('engine-mode-display');
        if (el && data.provider) {
            el.innerText = data.provider;
            el.style.color = data.provider.includes('GEMINI') ? 'var(--success)' : 'var(--warning)';
        }
    } catch(e) {}
}

// ─── Dashboard ──────────────────────────────────────────────────
async function loadDashboard() {
    try {
        const [kRes, iRes, lRes] = await Promise.all([
            fetch('/api/kpis'),
            fetch('/api/inventory'),
            fetch('/api/logs')
        ]);
        const kpis = await kRes.json();
        const inv  = await iRes.json();
        const logs = await lRes.json();

        const lowCount = inv.filter(i => (i.available_stock || 0) < (i.min_stock || 0)).length;

        document.getElementById('kpi-orders').innerText   = kpis.orders_today  || 0;
        document.getElementById('kpi-pending').innerText  = kpis.pending_orders || 0;
        document.getElementById('kpi-lowstock').innerText = lowCount || kpis.inventory_alerts || 0;
        document.getElementById('kpi-aiactions').innerText= kpis.agent_actions  || 0;
        
        // Agent breakdown
        const breakdown = kpis.agent_breakdown || {};
        const bdEl = document.getElementById('kpi-ai-breakdown');
        if (bdEl && Object.keys(breakdown).length > 0) {
            bdEl.innerHTML = Object.entries(breakdown).map(([ag, count]) => {
                return `${ag.padEnd(17, ' ')} ${count} actions`;
            }).join('<br>');
        }

        const badge = document.getElementById('db-inv-status');
        if (badge) {
            badge.innerText = lowCount > 0 ? `🟡 ${lowCount} LOW ITEMS` : '🟢 ALL NORMAL';
            badge.className = lowCount > 0 ? 'badge badge-warning' : 'badge badge-normal';
        }

        // Render Activity Feed
        const feed = document.getElementById('activity-feed');
        if (feed && logs && logs.length > 0) {
            feed.innerHTML = logs.slice(0, 15).map(log => {
                let icon = '🤖';
                if (log.agent_name.includes('Inventory')) icon = '📦';
                else if (log.agent_name.includes('Procurement')) icon = '🛒';
                else if (log.agent_name.includes('Delivery')) icon = '🚚';
                else if (log.agent_name.includes('Order')) icon = '📝';
                
                // Format relative time loosely
                const timeStr = log.timestamp.substring(11, 16); // Extract HH:MM
                
                return `
                <div class="step-card" style="margin:0;padding:0.8rem;border-left:3px solid ${log.status === 'ERROR' ? 'var(--danger)' : log.status === 'WARNING' ? 'var(--warning)' : 'var(--primary)'}">
                    <div style="color:var(--text-primary);font-weight:700;font-size:0.9rem;">${icon} ${log.agent_name}</div>
                    <div style="font-size:0.85rem;color:var(--text-secondary);margin:0.2rem 0;">${log.action}</div>
                    <div style="font-size:0.75rem;color:var(--text-muted);">${timeStr} ${log.order_id ? `| Order #${log.order_id}` : ''}</div>
                </div>`;
            }).join('');
        }

    } catch(e) { console.error('Dashboard error', e); }
}

// ─── Inventory ──────────────────────────────────────────────────
async function loadInventory() {
    try {
        const res   = await fetch('/api/inventory');
        const items = await res.json();
        const tbody = document.getElementById('inv-tbody');
        if (!tbody) return;

        tbody.innerHTML = items.map(i => {
            const avail  = i.available_stock || 0;
            const min    = i.min_stock || 0;
            const isLow  = avail < min;
            const pct    = Math.min(100, Math.round((avail / (min * 1.5 || 1)) * 100));
            const barClr = isLow ? 'var(--danger)' : 'var(--success)';
            return `
              <tr>
                <td><b>${i.ingredient_name}</b></td>
                <td>${(i.current_stock || 0).toFixed(1)} ${i.unit}</td>
                <td><span style="color:var(--warning)">${(i.reserved_stock || 0).toFixed(1)} ${i.unit}</span></td>
                <td><span style="color:var(--primary)">${(i.incoming_stock || 0).toFixed(1)} ${i.unit}</span></td>
                <td>
                  <b>${(i.available_stock || 0).toFixed(1)} ${i.unit}</b>
                  <div style="margin-top:4px;background:rgba(255,255,255,0.06);height:4px;border-radius:3px;overflow:hidden;width:80px;">
                    <div style="width:${pct}%;height:100%;background:${barClr};border-radius:3px;"></div>
                  </div>
                </td>
                <td>${(i.min_stock || 0).toFixed(1)} ${i.unit}</td>
                <td><span class="badge badge-${isLow ? 'low' : 'normal'}">${isLow ? '🔴 Low' : '🟢 Good'}</span></td>
              </tr>`;
        }).join('');

        // Alert box
        const lowItems = items.filter(i => (i.available_stock || 0) < (i.min_stock || 0));
        const alertBox = document.getElementById('inv-alert-box');
        if (alertBox) {
            if (!lowItems.length) {
                alertBox.innerHTML = '<div style="color:var(--success)">✅ All ingredient stocks are above minimum threshold.</div>';
            } else {
                alertBox.innerHTML = lowItems.map(i => {
                    const avail   = i.available_stock || 0;
                    const min     = i.min_stock || 0;
                    const deficit = (min - avail).toFixed(1);
                    return `
                      <div style="margin-bottom:0.8rem;">
                        <div style="font-weight:700;color:var(--text-primary);">${i.ingredient_name} (Available: ${avail.toFixed(1)} ${i.unit} | Min: ${min.toFixed(1)} ${i.unit})</div>
                        <div style="color:var(--primary);font-weight:700;margin:0.3rem 0;">🤖 AI Recommendation</div>
                        <div style="color:var(--text-secondary);font-size:0.9rem;">Available stock is below minimum threshold. Recommended purchase: <b>${deficit} ${i.unit}</b>.
                          <br><span class="badge badge-critical" style="margin-top:0.4rem;">⚠ PROCUREMENT REQUIRED</span>
                        </div>
                      </div>`;
                }).join('<hr style="border-color:var(--border);margin:0.8rem 0;">');
            }
        }
    } catch(e) { console.error('Inventory error', e); }
}

// ─── Suppliers ──────────────────────────────────────────────────
async function loadSuppliers() {
    try {
        const res  = await fetch('/api/suppliers');
        const sups = await res.json();
        const tbody = document.getElementById('sup-tbody');
        if (!tbody) return;

        tbody.innerHTML = sups.map(s => `
          <tr>
            <td><b>${s.name}</b></td>
            <td>${s.ingredient_name}</td>
            <td>₹${s.price_per_unit.toFixed(2)}</td>
            <td>${s.delivery_time_hrs} hrs</td>
            <td>${Math.round(s.reliability_score * 100)}%</td>
          </tr>`).join('');
    } catch(e) { console.error('Suppliers error', e); }
}

// ─── Orders ─────────────────────────────────────────────────────
async function loadOrders() {
    try {
        const res    = await fetch('/api/orders');
        const orders = await res.json();
        const tbody  = document.getElementById('ord-tbody');
        if (!tbody) return;

        tbody.innerHTML = orders.map(o => {
            const st  = (o.status || 'Pending').toLowerCase().replace(/\s+/g, '-');
            return `
              <tr>
                <td><b>#${o.id}</b></td>
                <td>${o.customer_name}</td>
                <td><b>${o.product_name}</b></td>
                <td>${o.quantity}</td>
                <td><span class="badge badge-${st === 'delivered' || st === 'out-for-delivery' || st === 'completed' ? 'normal' : st === 'processing' || st === 'preparing' ? 'warning' : 'pending'}">${o.status}</span></td>
                <td><b style="color:var(--primary);">${o.ai_status || '🧠 Pending'}</b></td>
              </tr>`;
        }).join('');
    } catch(e) { console.error('Orders error', e); }
}

// ─── Quick Demo ─────────────────────────────────────────────────
function quickDemo() {
    document.getElementById('f-cust').value = 'Aritra';
    document.getElementById('f-food').value = 'Chicken Biryani';
    document.getElementById('f-qty').value  = '10';
    document.getElementById('f-loc').value  = 'New Town';
    updateIngredientPreview();
    toast('Quick demo loaded!');
    // Switch to form tab then submit
    switchTab('create-order', document.querySelector('[onclick*="create-order"]'));
    setTimeout(() => document.getElementById('orderForm').dispatchEvent(new Event('submit', { cancelable: true, bubbles: true })), 300);
}

// ═══════════════════════════════════════════════════════════════
//  CORE AGENT PIPELINE FUNCTION
// ═══════════════════════════════════════════════════════════════

async function submitOrder(e) {
    e.preventDefault();

    const custName = document.getElementById('f-cust').value.trim() || 'Aritra';
    const foodItem = document.getElementById('f-food').value || 'Chicken Biryani';
    const quantity = parseInt(document.getElementById('f-qty').value || '10');
    const location = document.getElementById('f-loc').value.trim() || 'New Town';

    // Disable submit button
    const btn = document.getElementById('submitBtn');
    if (btn) { btn.disabled = true; btn.innerText = '⏳ Processing...'; }

    // Navigate to pipeline view
    switchTab('pipeline', document.getElementById('nav-pipeline'));
    resetPipeline();

    // ── Step 0: Start ──────────────────────────────────────────
    setProgress(5, 'Sending order to AI agents...');

    // Show the order details banner immediately
    addPipelineStep({
        agent: '📝 ORDER RECEIVED',
        badgeClass: 'badge-normal',
        badgeText: '✓ QUEUED',
        action: 'Customer order dispatched to multi-agent system',
        body: `
          <b>Customer:</b> ${custName} &nbsp;|&nbsp; <b>Location:</b> ${location}<br>
          <b>Food Item:</b> ${foodItem} &nbsp;|&nbsp; <b>Quantity:</b> ${quantity}<br>
          <br><b>Triggering Agentic Workflow...</b> <span class="pulse-dot" style="display:inline-block;vertical-align:middle;margin-left:4px;"></span>
        `,
        state: 'done-ok'
    });

    await delay(700);

    // ── Step 1: ORDER AGENT (client-side preview while API runs) ─
    setProgress(20, '🤖 Order Agent: Mapping ingredients...');
    const localRecipe = RECIPES[foodItem] || {};
    const requirements = {};
    const ingredientLines = Object.entries(localRecipe).map(([ing, pp]) => {
        const tot = (pp * quantity).toFixed(2);
        requirements[ing] = parseFloat(tot);
        const unit = ing === 'Oil' ? 'L' : 'kg';
        return `• ${ing}: required = <b style="color:var(--primary)">${tot} ${unit}</b>`;
    }).join('<br>');

    addPipelineStep({
        agent: '🤖 1. ORDER AGENT',
        badgeClass: 'badge-normal',
        badgeText: '✓ UNDERSTOOD',
        action: 'Receives order, calculates required ingredients from recipe database',
        body: `
          <b>Product:</b> ${foodItem} × ${quantity}<br>
          <b>Customer:</b> ${custName} | <b>Location:</b> ${location}<br><br>
          <b>Ingredient Breakdown Calculated:</b><br>${ingredientLines || '• No recipe found'}
        `,
        state: 'done-ok'
    });
    await delay(800);

    // ── Fire the actual backend API call ───────────────────────
    let apiData = null;
    try {
        const apiProm = fetch('/api/process-order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ customer_name: custName, food_item: foodItem, quantity, delivery_location: location })
        });

        // Animate step 2 (inventory) while waiting
        setProgress(40, '📦 Inventory Agent: Auditing stock...');
        const invCard = addPipelineStep({
            agent: '📦 2. INVENTORY AGENT',
            badgeClass: 'badge-warning',
            badgeText: '⏳ AUDITING...',
            action: 'Reads Firebase/DB stock levels, compares with ingredient requirements',
            body: `<div class="pulse-dot" style="display:inline-block;vertical-align:middle;margin-right:6px;"></div> Checking stock for: ${Object.keys(requirements).join(', ')}...`,
            state: 'loading'
        });

        const apiRes  = await apiProm;
        apiData = await apiRes.json();

        if (apiData.status === 'error') throw new Error(apiData.message);

        // Now update inventory card with real data from API
        const shortages = apiData.shortages || [];
        const invSnapshot = apiData.agent_log?.find(l => l.agent === 'Inventory Agent');
        const stockMap = invSnapshot?.details?.stock_map || {};

        const invLines = Object.entries(apiData.ingredient_requirements || requirements).map(([ing, req]) => {
            const avail = stockMap[ing] !== undefined ? stockMap[ing].toFixed(2) : '?';
            const unit  = ing === 'Oil' ? 'L' : 'kg';
            const shortage = shortages.find(s => s.ingredient === ing);
            if (shortage) {
                const sevClr = shortage.severity === 'CRITICAL' ? 'var(--danger)' : 'var(--warning)';
                const sev    = shortage.severity || 'LOW';
                return `<span style="color:${sevClr}">🔴 <b>${ing}</b>: ${avail} ${unit} available | Required: ${req} ${unit} | Deficit: <b>${shortage.deficit} ${unit}</b> [${sev}]</span>`;
            }
            return `<span style="color:var(--success)">✓ <b>${ing}</b>: ${avail} ${unit} available | Required: ${req} ${unit} | OK</span>`;
        }).join('<br>');

        let invExtra = '';
        if (shortages.length > 0) {
            const criticalCount = shortages.filter(s => s.severity === 'CRITICAL').length;
            invExtra = `<br><br><b style="color:var(--danger);">🔴 ${criticalCount} CRITICAL, ${shortages.length - criticalCount} LOW SHORTAGE(S) DETECTED</b><br>`;
            shortages.forEach(s => {
                invExtra += `• <b>${s.ingredient}</b> [${s.severity}]: needs ${s.deficit} more ${s.unit} → ordering ${s.reorder_qty} ${s.unit} (with 20% buffer)<br>`;
            });
            invExtra += `<br><b style="color:var(--warning);">→ Decision Node: STOCK LOW → Routing to Procurement Agent</b>`;
        } else {
            invExtra = `<br><br><b style="color:var(--success);">✅ All ingredients verified and sufficient.</b><br>→ Decision Node: STOCK OK → Routing directly to Delivery Agent.`;
        }

        updatePipelineStep(invCard, {
            badgeClass: shortages.length ? 'badge-warning' : 'badge-normal',
            badgeText:  shortages.length ? `⚠️ ${shortages.length} SHORTAGE(S)` : '✓ ALL IN STOCK',
            body:       invLines + invExtra,
            state:      shortages.length ? 'done-warn' : 'done-ok'
        });

        await delay(600);

        // ── Step 3: PROCUREMENT AGENT ──────────────────────────
        const proc = apiData.procurement || {};
        if (!apiData.needs_procurement) {
            setProgress(65, '🛒 Procurement: Not required...');
            addPipelineStep({
                agent: '🛒 3. PROCUREMENT AGENT',
                badgeClass: 'badge-normal',
                badgeText: '✓ SKIPPED',
                action: 'Inventory sufficient — no purchase order needed',
                body: `✅ All required ingredients confirmed in stock.<br>
                       No procurement required.<br><br>
                       <b>→ Routing directly to Kitchen Preparation.</b>`,
                state: 'skipped'
            });
        } else {
            setProgress(65, '🛒 Procurement Agent: Evaluating suppliers...');
            const decisions = proc.decisions || [];
            const totalWaitHrs = proc.total_wait_hrs || 0;
            const totalCost = proc.total_procurement_cost || 0;

            let procBody = '';
            decisions.forEach((d, idx) => {
                const sups = d.all_suppliers || [];
                const best = d.selected_supplier;
                const sevClr = d.severity === 'CRITICAL' ? 'var(--danger)' : 'var(--warning)';

                procBody += `<div style="margin-bottom:1rem;padding:0.8rem;background:rgba(0,0,0,0.3);border-radius:8px;">`;
                procBody += `<b style="color:${sevClr}">[${d.severity}] ${d.ingredient}</b> — Deficit: ${d.deficit} kg → Ordering: <b>${d.reorder_qty} kg</b> (with 20% buffer)<br><br>`;

                if (sups.length > 1) {
                    procBody += `<b>Candidate Suppliers (AI Multi-Criteria Scoring):</b><br>`;
                    sups.slice(0, 4).forEach(s => {
                        const isBest = s.name === best.name;
                        const scoreBar = Math.round((s.composite_score || 0) * 100);
                        const barClr  = isBest ? 'var(--success)' : 'rgba(255,255,255,0.3)';
                        procBody += `<div style="margin:3px 0;display:flex;align-items:center;gap:8px;">`;
                        procBody += `<span style="font-size:0.85rem;width:200px;${isBest ? 'color:var(--success);font-weight:700' : ''}">${isBest ? '🏆 ' : ''}${s.name}</span>`;
                        procBody += `<span style="font-size:0.8rem;color:var(--text-muted);width:180px;">₹${s.price_per_unit}/kg | ${s.delivery_time_hrs}h | ${Math.round(s.reliability_score*100)}%</span>`;
                        procBody += `<div style="flex:1;background:rgba(255,255,255,0.06);height:6px;border-radius:3px;overflow:hidden;">`;
                        procBody += `<div style="width:${scoreBar}%;height:100%;background:${barClr};"></div></div>`;
                        procBody += `<span style="font-size:0.8rem;color:${isBest?'var(--success)':'var(--text-muted)'};width:40px;">${(s.composite_score||0).toFixed(2)}</span>`;
                        procBody += `</div>`;
                    });
                    procBody += `<br>`;
                }

                procBody += `<b style="color:var(--success);">🧠 AI DECISION:</b> <b>${best.name}</b> selected<br>`;
                procBody += `<b>Order:</b> ${d.reorder_qty} kg | <b>Cost:</b> ₹${d.total_cost} | <b>Supplier ETA:</b> ${best.delivery_time_hrs} hrs<br>`;
                const reasoning = d.reasoning ? d.reasoning.split('\n').pop() : '';
                if (reasoning) procBody += `<span style="color:var(--text-muted);font-size:0.88rem;">${reasoning}</span><br>`;
                procBody += `<b>PO #${d.po_id}</b> created & approved.`;
                procBody += `</div>`;
            });

            procBody += `<div style="background:rgba(251,191,36,0.08);border:1px solid rgba(251,191,36,0.3);border-radius:8px;padding:0.8rem;margin-top:0.5rem;">`;
            procBody += `⏳ <b style="color:var(--warning);">Kitchen must wait ${totalWaitHrs} hrs for supplier delivery.</b><br>`;
            procBody += `Total procurement cost: <b>₹${totalCost.toFixed(2)}</b>`;
            procBody += `</div>`;

            addPipelineStep({
                agent: '🛒 3. PROCUREMENT AGENT',
                badgeClass: 'badge-normal',
                badgeText: `✓ ${decisions.length} PO(s) CREATED`,
                action: 'Multi-criteria supplier scoring: Speed×0.40 + Reliability×0.35 + Price×0.25',
                body: procBody,
                state: 'done-ok'
            });
        }

        await delay(600);

        // ── Step 4: KITCHEN ─────────────────────────────────────
        setProgress(85, '🍳 Kitchen preparation...');
        const delivery = apiData.delivery || {};
        const procWaitMin = delivery.procurement_wait_min || 0;
        const prepMin     = delivery.prep_min || 15;

        let kitchenBadgeClass = 'badge-normal';
        let kitchenBadgeText  = '✓ QUEUED';
        let kitchenBody       = '';
        let kitchenState      = 'done-ok';

        if (procWaitMin > 0) {
            kitchenBadgeClass = 'badge-warning';
            kitchenBadgeText  = `⏳ WAITING FOR STOCK (${procWaitMin} min)`;
            kitchenBody = `
              <div style="background:rgba(251,191,36,0.08);border-left:3px solid var(--warning);padding:0.8rem;border-radius:6px;margin-bottom:0.6rem;">
                <b style="color:var(--warning);">⚠️ Kitchen cannot start yet.</b><br>
                Waiting for supplier to deliver ingredients: <b>${procWaitMin} min</b> (${(procWaitMin/60).toFixed(1)} hrs)<br>
                Once stock arrives → Kitchen will begin preparation immediately.
              </div>
              <b>Estimated kitchen prep time:</b> ${prepMin} min<br>
              <b>Order #${apiData.order_id}:</b> In queue — will start after stock arrives.`;
            kitchenState = 'done-warn';
        } else {
            kitchenBody = `
              <b>Inventory Status:</b> All ingredients verified ✓<br>
              <b>Kitchen Queue:</b> Order #${apiData.order_id || '—'} approved for immediate preparation.<br>
              <b>Estimated prep time:</b> ${prepMin} min`;
        }

        addPipelineStep({
            agent: '🍳 4. KITCHEN PREPARATION',
            badgeClass: kitchenBadgeClass,
            badgeText:  kitchenBadgeText,
            action: procWaitMin > 0
                ? 'Waiting for procured ingredients to arrive before starting'
                : 'Ingredients verified — order queued for cooking',
            body:  kitchenBody,
            state: kitchenState
        });
        await delay(500);

        // ── Step 5: DELIVERY AGENT ─────────────────────────────
        setProgress(100, '🚚 Delivery Agent: Assigning rider...');
        const orderStage     = apiData.order_stage || 'OUT_FOR_DELIVERY';
        const transitMin     = delivery.transit_min || 10;
        const totalEtaMin    = delivery.total_eta_min || (prepMin + transitMin);
        const isScheduled    = orderStage === 'SCHEDULED';

        let deliveryBadgeClass = isScheduled ? 'badge-warning' : 'badge-normal';
        let deliveryBadgeText  = isScheduled ? `⏳ PRE-ASSIGNED (departs in ${procWaitMin + prepMin} min)` : '✓ RIDER DISPATCHED NOW';

        let etaBreakdown = '';
        if (procWaitMin > 0) {
            etaBreakdown = `
              <div style="background:rgba(0,0,0,0.3);padding:0.8rem;border-radius:8px;margin:0.8rem 0;font-family:'JetBrains Mono',monospace;font-size:0.88rem;">
                <div style="margin-bottom:0.4rem;">📦 Supplier delivery wait : <b style="color:var(--warning);">${procWaitMin} min (${(procWaitMin/60).toFixed(1)} hrs)</b></div>
                <div style="margin-bottom:0.4rem;">🍳 Kitchen preparation     : <b>${prepMin} min</b></div>
                <div style="margin-bottom:0.4rem;">🏍 Transit to ${location}  : <b>${transitMin} min</b></div>
                <div style="border-top:1px solid var(--border);margin-top:0.4rem;padding-top:0.4rem;">
                  🕐 <b>TOTAL ETA: <span style="color:var(--warning);font-size:1.05em;">${totalEtaMin} min (${Math.floor(totalEtaMin/60)}h ${totalEtaMin%60}m)</span></b>
                </div>
              </div>
              <b style="color:var(--warning);">⚠️ Order status: SCHEDULED</b> — Cannot dispatch until kitchen is ready.<br>
              Rider pre-assigned and will depart as soon as preparation completes.`;
        } else {
            etaBreakdown = `
              <div style="background:rgba(0,0,0,0.3);padding:0.8rem;border-radius:8px;margin:0.8rem 0;font-family:'JetBrains Mono',monospace;font-size:0.88rem;">
                <div style="margin-bottom:0.4rem;">🍳 Kitchen preparation : <b>${prepMin} min</b></div>
                <div style="margin-bottom:0.4rem;">🏍 Transit to ${location} : <b>${transitMin} min</b></div>
                <div style="border-top:1px solid var(--border);margin-top:0.4rem;padding-top:0.4rem;">
                  🕐 <b>TOTAL DOORSTEP ETA: <span style="color:var(--success);font-size:1.05em;">${totalEtaMin} min</span></b>
                </div>
              </div>
              <b style="color:var(--success);">✅ Order status: OUT FOR DELIVERY</b>`;
        }

        addPipelineStep({
            agent: '🚚 5. DELIVERY AGENT',
            badgeClass: deliveryBadgeClass,
            badgeText:  deliveryBadgeText,
            action: isScheduled
                ? 'Rider pre-assigned — awaiting kitchen confirmation before dispatch'
                : 'Rider dispatched — en route to customer',
            body: `
              <b>Available Riders:</b> ${delivery.available_riders || 8} active riders<br>
              <b>Assigned Rider:</b> ${delivery.rider_name || 'Rahul Kumar'} (${delivery.vehicle || 'EV Scooter'}) from ${delivery.rider_location || 'Nearby'}<br>
              <b>Distance:</b> ${delivery.distance_km || 3.2} km to ${location}<br>
              ${etaBreakdown}
            `,
            state: isScheduled ? 'done-warn' : 'done-ok'
        });

        await delay(400);

        // ── Final ──────────────────────────────────────────────
        document.getElementById('progress-label').innerText = '✅ Autonomous Workflow Completed';
        document.getElementById('progress-badge').innerText = 'COMPLETED';
        document.getElementById('progress-badge').className = 'badge badge-normal';
        document.getElementById('pipeline-title').innerText = '✅ Autonomous Workflow Completed';

        toast(`Order #${apiData.order_id} processed autonomously!`, 'success');
        showFinalCard(apiData, custName, foodItem, quantity, delivery);

        loadDashboard();

    } catch(err) {
        console.error('Pipeline error', err);
        setProgress(100, `❌ Error: ${err.message}`);
        document.getElementById('progress-badge').innerText = 'ERROR';
        document.getElementById('progress-badge').className = 'badge badge-critical';
        toast(`Error: ${err.message}`, 'error');
    }

    if (btn) { btn.disabled = false; btn.innerText = '⚡ PROCESS WITH AI'; }
}

// ─── Pipeline Helpers ───────────────────────────────────────────
function resetPipeline() {
    document.getElementById('pipeline-steps').innerHTML = '';
    document.getElementById('progress-bar').style.width = '0%';
    document.getElementById('progress-label').innerText = 'Initialising Agents...';
    document.getElementById('progress-badge').className = 'badge badge-warning';
    document.getElementById('progress-badge').innerText = 'PROCESSING';
    document.getElementById('pipeline-title').innerText = '🤖 AI Agent Pipeline';
    document.getElementById('final-card').classList.add('hidden');
}

function setProgress(pct, label) {
    document.getElementById('progress-bar').style.width = `${pct}%`;
    if (label) document.getElementById('progress-label').innerText = label;
}

function addPipelineStep({ agent, badgeClass, badgeText, action, body, state }) {
    const container = document.getElementById('pipeline-steps');
    const card = document.createElement('div');
    card.className = `step-card ${state || ''}`;
    card.style.animation = 'fadeSlideIn 0.4s ease-out';
    card.innerHTML = `
      <div class="step-agent-title">
        <span style="font-weight:800;font-size:1rem;">${agent}</span>
        <span class="badge ${badgeClass}">${badgeText}</span>
      </div>
      <div class="step-action" style="margin-bottom:0.6rem;">${action}</div>
      <div class="step-body">${body}</div>
    `;
    container.appendChild(card);
    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    return card;
}

function updatePipelineStep(card, { badgeClass, badgeText, body, state }) {
    if (!card) return;
    const badge = card.querySelector('.badge');
    if (badge) { badge.className = `badge ${badgeClass}`; badge.innerText = badgeText; }
    const bodyEl = card.querySelector('.step-body');
    if (bodyEl) bodyEl.innerHTML = body;
    card.className = `step-card ${state || ''}`;
}

function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

// ─── Final Decision Card ────────────────────────────────────────
function showFinalCard(data, custName, foodItem, quantity, delivery) {
    const finalCard = document.getElementById('final-card');
    finalCard.classList.remove('hidden');
    finalCard.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Order title
    document.getElementById('dec-order-title').innerText = `ORDER #${data.order_id || '—'} SUMMARY:`;

    // Steps checklist
    const steps = data.final_decision?.steps || [];
    const stepsEl = document.getElementById('dec-steps-list');
    if (steps.length) {
        stepsEl.innerHTML = steps.map(s => {
            const icon = s.ok ? '✓' : '⚠️';
            const clr  = s.ok ? 'inherit' : 'var(--warning)';
            return `<div style="color:${clr}">${icon} ${s.check}<span style="color:var(--text-muted);margin-left:0.5rem;font-size:0.85em;">(${s.detail})</span></div>`;
        }).join('');
    } else {
        // Fallback if no steps
        const shortages = data.shortages || [];
        const proc = (data.procurement?.decisions || [])[0];
        let html = `<div>✓ Order understood <span style="color:var(--text-muted);font-size:0.85em;">(${custName} • ${foodItem} × ${quantity})</span></div>`;
        html += `<div>✓ Inventory checked <span style="color:var(--text-muted);font-size:0.85em;">(All ingredients audited)</span></div>`;
        if (shortages.length) {
            shortages.forEach(s => {
                html += `<div style="color:var(--warning)">⚠️ Stock shortage detected <span style="color:var(--text-muted);font-size:0.85em;">(${s.ingredient} deficit ${s.deficit} ${s.unit})</span></div>`;
            });
        }
        if (proc) {
            html += `<div>✓ Supplier selected <span style="color:var(--text-muted);font-size:0.85em;">(${proc.selected_supplier.name})</span></div>`;
            html += `<div>✓ Procurement created <span style="color:var(--text-muted);font-size:0.85em;">(PO #${proc.po_id} | ₹${proc.total_cost})</span></div>`;
        }
        html += `<div>✓ Delivery assigned <span style="color:var(--text-muted);font-size:0.85em;">(${delivery?.rider_name || 'Rider #04'} | ETA: ${delivery?.eta_min || 25} min)</span></div>`;
        stepsEl.innerHTML = html;
    }

    // Reasoning drawer
    const rSteps = document.getElementById('reasoning-steps');
    const shortages = data.shortages || [];
    const proc = (data.procurement?.decisions || [])[0];
    let reasoningItems = [
        `Customer <b>${custName}</b> requested <b>${quantity}× ${foodItem}</b>.`,
        `Order Agent calculated ingredient requirements from recipe database.`,
        `Inventory Agent audited all required ingredients against current DB stock.`,
    ];
    if (shortages.length) {
        shortages.forEach(s => reasoningItems.push(`Shortage detected: <b>${s.ingredient}</b> — need ${s.required} ${s.unit}, only ${s.available} ${s.unit} available (deficit: ${s.deficit} ${s.unit}).`));
    } else {
        reasoningItems.push('All ingredients were found in sufficient stock — procurement skipped.');
    }
    if (proc) {
        const sups = proc.all_suppliers || [];
        if (sups.length > 1) {
            const names = sups.map(s => `${s.name} (₹${s.price_per_unit}/kg, ${s.delivery_time_hrs}h, ${Math.round(s.reliability_score*100)}%)`).join('; ');
            reasoningItems.push(`Procurement Agent evaluated ${sups.length} candidate suppliers: ${names}.`);
        }
        reasoningItems.push(`<b>${proc.selected_supplier.name}</b> was selected for its optimal delivery speed (${proc.selected_supplier.delivery_time_hrs}h) and high reliability (${Math.round(proc.selected_supplier.reliability_score*100)}%) at ₹${proc.selected_supplier.price_per_unit}/kg.`);
    }
    reasoningItems.push(`Delivery Agent assigned <b>${delivery?.rider_name || 'Rider #04'}</b> for ${delivery?.distance_km || 3.2} km — ETA ${delivery?.eta_min || 25} minutes.`);

    rSteps.innerHTML = reasoningItems.map(r => `<li>${r}</li>`).join('');
    document.getElementById('reasoning-conclusion').innerText = 'Decision: Autonomous multi-agent workflow completed successfully. Order fulfilled.';

    // Procurement table
    if (proc && proc.all_suppliers?.length > 1) {
        document.getElementById('procurement-table-wrap').classList.remove('hidden');
        const tbody = document.getElementById('procurement-table-body');
        tbody.innerHTML = proc.all_suppliers.map(s => {
            const isBest = s.name === proc.selected_supplier.name;
            return `<tr class="${isBest ? 'selected-row' : ''}">
              <td>${s.name}${isBest ? ' 🏆' : ''}</td>
              <td>₹${s.price_per_unit}/kg</td>
              <td>${s.delivery_time_hrs} hrs</td>
              <td>${Math.round(s.reliability_score * 100)}%</td>
              <td>${isBest ? '<span class="badge badge-normal">✓ SELECTED</span>' : '<span style="color:var(--text-muted);">—</span>'}</td>
            </tr>`;
        }).join('');
    }
}

function toggleReasoning() {
    document.getElementById('reasoning-drawer')?.classList.toggle('hidden');
}

// ─── Inject slide-in animation ──────────────────────────────────
const styleTag = document.createElement('style');
styleTag.textContent = `
@keyframes fadeSlideIn {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}`;
document.head.appendChild(styleTag);
