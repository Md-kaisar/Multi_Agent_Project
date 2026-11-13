import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def apply_custom_css():
    st.markdown("""
    <style>
    /* Dark glassmorphic aesthetic for FoodFlow AI */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #f8fafc;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }
    
    /* Main title formatting */
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #94a3b8;
        margin-bottom: 1.5rem;
    }
    
    /* Card design */
    .kpi-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(12px);
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        border-color: rgba(56, 189, 248, 0.4);
    }
    .kpi-title {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94a3b8;
        margin-bottom: 0.4rem;
    }
    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #f8fafc;
    }
    .kpi-sub {
        font-size: 0.8rem;
        color: #38bdf8;
        margin-top: 0.2rem;
    }
    
    /* Status Badges */
    .badge {
        display: inline-block;
        padding: 0.25em 0.6em;
        font-size: 0.75rem;
        font-weight: 600;
        border-radius: 6px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .badge-normal {
        background-color: rgba(34, 197, 94, 0.2);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.4);
    }
    .badge-low {
        background-color: rgba(234, 179, 8, 0.2);
        color: #facc15;
        border: 1px solid rgba(234, 179, 8, 0.4);
    }
    .badge-critical {
        background-color: rgba(239, 68, 68, 0.2);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.4);
    }
    
    /* Agent Card */
    .agent-card {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }
    .agent-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #38bdf8;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Live Step Logs */
    .step-log-box {
        background: #020617;
        border-left: 4px solid #38bdf8;
        padding: 0.8rem 1rem;
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.88rem;
        margin-bottom: 0.6rem;
    }
    </style>
    """, unsafe_allow_html=True)

def render_kpi(title, value, subtext, icon="📊"):
    html = f"""
    <div class="kpi-card">
        <div class="kpi-title">{icon} {title}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{subtext}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_badge(status):
    status_str = str(status).upper()
    if status_str in ["NORMAL", "COMPLETED", "DELIVERED", "AVAILABLE", "APPROVED"]:
        css_class = "badge-normal"
    elif status_str in ["LOW", "PREPARING", "PENDING", "IN_TRANSIT", "WARNING"]:
        css_class = "badge-low"
    else:
        css_class = "badge-critical"
    return f'<span class="badge {css_class}">{status_str}</span>'

def plot_orders_chart(df):
    if df.empty:
        fig = px.bar(title="No order data available")
    else:
        fig = px.bar(
            df,
            x='created_at',
            y='quantity',
            color='product_name',
            title="<b>Real-time Order Volume Trend</b>",
            color_discrete_sequence=px.colors.qualitative.Pastel,
            template="plotly_dark"
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="#f8fafc"),
            margin=dict(l=20, r=20, t=40, b=20)
        )
    return fig

def plot_top_items_chart(df):
    if df.empty:
        fig = px.pie(title="No item data available")
    else:
        item_summary = df.groupby('product_name')['quantity'].sum().reset_index()
        fig = px.pie(
            item_summary,
            values='quantity',
            names='product_name',
            title="<b>Product Sales Distribution</b>",
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.Plasma_r,
            template="plotly_dark"
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="#f8fafc"),
            margin=dict(l=20, r=20, t=40, b=20)
        )
    return fig

def plot_inventory_gauge(inventory_items):
    df = pd.DataFrame(inventory_items)
    if df.empty:
        fig = px.bar(title="No inventory data")
    else:
        fig = px.bar(
            df,
            x='ingredient_name',
            y=['current_stock', 'min_stock'],
            barmode='group',
            title="<b>Current Stock vs Minimum Reorder Threshold</b>",
            labels={'value': 'Quantity (kg/L)', 'ingredient_name': 'Raw Material'},
            color_discrete_map={'current_stock': '#38bdf8', 'min_stock': '#ef4444'},
            template="plotly_dark"
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="#f8fafc"),
            margin=dict(l=20, r=20, t=40, b=20)
        )
    return fig
