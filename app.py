"""
ATROPOS Finance AI — Multi-Agent Financial Intelligence Dashboard
=================================================================
Run:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import time
from datetime import datetime
from mock_data import generate_mock_transactions
from data_processor import load_and_parse_csv, standardize_dataframe
from agents import (
    map_columns, run_sanitizer, run_forensic_audit,
    run_wealth_architect, chat_with_data,
    run_forecast, generate_smart_alerts, get_peer_comparison,
    run_agent_debate, get_metrics, reset_metrics,
    INDIA_URBAN_BENCHMARKS,
)
import streamlit.components.v1 as components
from report_gen import generate_pdf_report

# ── Config ────────────────────────────────────────────────────────
st.set_page_config(page_title="ATROPOS Finance AI", page_icon="⚔️", layout="wide", initial_sidebar_state="expanded")

P = ["#8b5cf6","#06b6d4","#f59e0b","#10b981","#ef4444","#ec4899","#f97316","#84cc16","#6366f1","#14b8a6"]

def _rgba(h, a=1.0):
    r,g,b = int(h[1:3],16), int(h[3:5],16), int(h[5:7],16)
    return f"rgba({r},{g},{b},{a})"

def _layout(**kw):
    base = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=TEXT2, size=11, family="Inter"),
                margin=dict(t=24, b=30, l=45, r=15),
                xaxis=dict(gridcolor=GRID, showgrid=True, zeroline=False),
                yaxis=dict(gridcolor=GRID, showgrid=True, zeroline=False),
                hoverlabel=dict(bgcolor=CARD, font_size=12, font_family="Inter", font_color=TEXT1))
    base.update(kw)
    return base

# ── Theme ─────────────────────────────────────────────────────────
if "light_mode" not in st.session_state:
    st.session_state.light_mode = False

lm = st.session_state.light_mode
BG      = "#f7f8fa" if lm else "#0b0b10"
CARD    = "#ffffff" if lm else "#111118"
BORDER  = "#e2e4e9" if lm else "#1c1c28"
TEXT1   = "#111827" if lm else "#e4e4ec"
TEXT2   = "#6b7280" if lm else "#5a5a70"
TEXT3   = "#9ca3af" if lm else "#4e4e64"
GRID    = "#e5e7eb" if lm else "#1c1c28"

# ── CSS ───────────────────────────────────────────────────────────
st.markdown(f"""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
    p, label, h1, h2, h3, h4, h5, h6, div, input, textarea, button,
    td, th, li, [data-testid="stMarkdownContainer"], [data-testid="stText"],
    .stRadio label, .stSelectbox label, .stFileUploader label {{
        font-family: 'Inter', -apple-system, sans-serif !important;
    }}
    span[data-testid="stIconMaterial"], .material-symbols-rounded, [class*="material-symbols"] {{
        font-family: 'Material Symbols Rounded', sans-serif !important;
    }}
    .stApp {{ background: {BG} !important; }}

    div[data-testid="stMetric"] {{
        background: {CARD} !important; border: 1px solid {BORDER} !important;
        border-radius: 12px !important; padding: 20px 16px !important;
    }}
    div[data-testid="stMetric"]:hover {{ border-color: {"#d0d5dd" if lm else "#2a2a3a"} !important; }}
    div[data-testid="stMetric"] label {{
        color: {TEXT2} !important; font-size: 0.65rem !important;
        text-transform: uppercase !important; letter-spacing: 1.8px !important; font-weight: 600 !important;
    }}
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
        color: {TEXT1} !important; font-size: 1.4rem !important; font-weight: 700 !important;
    }}
    div[data-testid="stMetric"] [data-testid="stMetricDelta"] {{ font-size: 0.7rem !important; }}

    section[data-testid="stSidebar"] {{
        background: {"#f0f2f5" if lm else "#08080c"} !important;
        border-right: 1px solid {"#d0d5dd" if lm else "#131320"} !important;
    }}
    section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] li,
    section[data-testid="stSidebar"] label {{
        color: {"#166534" if lm else "#4ade80"} !important; font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.75rem !important; line-height: 1.55 !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span {{
        color: {"#166534" if lm else "#4ade80"} !important; font-family: 'JetBrains Mono', monospace !important;
    }}
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {{
        color: {"#166534" if lm else "#4ade80"} !important; font-family: 'JetBrains Mono', monospace !important; font-size: 0.95rem !important;
    }}
    section[data-testid="stSidebar"] code {{
        color: {"#166534" if lm else "#4ade80"} !important; background: {"#e2e8f0" if lm else "#0a0a0e"} !important;
        font-family: 'JetBrains Mono', monospace !important; font-size: 0.68rem !important;
        white-space: pre-wrap !important;
    }}
    section[data-testid="stSidebar"] hr {{ border-color: {"#d0d5dd" if lm else "#132013"} !important; }}
    section[data-testid="stSidebar"] [data-testid="stStatusWidget"] {{
        background: {"#e2e8f0" if lm else "#0f0f14"} !important;
    }}

    details[data-testid="stExpander"] {{
        border: 1px solid {BORDER} !important; border-radius: 10px !important;
        margin-bottom: 6px !important; background: {CARD} !important;
    }}
    details[data-testid="stExpander"] summary {{
        padding: 10px 14px !important; font-size: 0.84rem !important;
        font-weight: 600 !important; color: {TEXT1} !important;
    }}
    details[data-testid="stExpander"] > div {{ padding: 0 14px 12px 14px !important; }}

    .stButton > button[kind="primary"] {{
        background: #8b5cf6 !important; color: #fff !important;
        border: none !important; border-radius: 8px !important; font-weight: 600 !important;
    }}
    .stButton > button[kind="primary"]:hover {{ background: #7c3aed !important; }}
    .stDownloadButton > button {{
        background: {CARD} !important; border: 1px solid {BORDER} !important;
        border-radius: 8px !important; color: #8b5cf6 !important; font-weight: 500 !important;
    }}
    .stDownloadButton > button:hover {{ border-color: #8b5cf6 !important; }}

    .stChatMessage {{
        background: {CARD} !important; border: 1px solid {BORDER} !important; border-radius: 10px !important;
    }}

    .stTabs [data-baseweb="tab-list"] {{ gap: 0; background: transparent; }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent !important; color: {TEXT2} !important;
        border: none !important; padding: 8px 18px !important; font-weight: 500 !important; font-size: 0.82rem !important;
    }}
    .stTabs [aria-selected="true"] {{ color: {TEXT1} !important; border-bottom: 2px solid #8b5cf6 !important; }}

    .stMarkdown h2 {{ color: {TEXT1} !important; font-size: 1.15rem !important; font-weight: 700 !important; }}
    .stMarkdown h3 {{ color: {"#374151" if lm else "#b0b0c4"} !important; font-size: 0.95rem !important; font-weight: 600 !important; }}
    .stMarkdown p {{ line-height: 1.65 !important; color: {"#6b7280" if lm else "#8b8b9e"} !important; }}
    hr {{ border-color: {BORDER} !important; margin: 0.6rem 0 !important; }}
    .stPlotlyChart {{ margin-top: 2px !important; }}

    .sec-title {{ color: {TEXT1}; font-size: 1.05rem; font-weight: 700; margin: 0 0 2px 0; letter-spacing: -0.3px; }}
    .sec-sub {{ color: {TEXT3}; font-size: 0.75rem; margin: 0 0 8px 0; }}

    .alert-card {{ border-radius: 8px; padding: 10px 14px; margin-bottom: 6px; }}
    .alert-danger  {{ background: rgba(239,68,68,0.08); border-left: 3px solid #ef4444; }}
    .alert-warning {{ background: rgba(245,158,11,0.08); border-left: 3px solid #f59e0b; }}
    .alert-info    {{ background: rgba(6,182,212,0.08); border-left: 3px solid #06b6d4; }}
    .alert-success {{ background: rgba(16,185,129,0.08); border-left: 3px solid #10b981; }}
    .alert-title {{ color: {TEXT1}; font-weight: 600; font-size: 0.82rem; margin: 0; }}
    .alert-detail {{ color: {TEXT2}; font-size: 0.72rem; margin: 2px 0 0 0; }}

    .pipe-step {{ display: flex; align-items: center; gap: 8px; padding: 5px 0; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; }}
    .pipe-dot {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }}
    .pipe-done {{ background: #10b981; }}
    .pipe-wait {{ background: {"#d0d5dd" if lm else "#2a2a3a"}; }}
    .pipe-name {{ color: {"#166534" if lm else "#4ade80"}; }}
    .pipe-time {{ color: {"#6b7280" if lm else "#3a5a3a"}; margin-left: auto; }}
    @keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:0.4}} }}

    .metric-strip {{ display:flex; gap:16px; margin:4px 0 12px 0; flex-wrap:wrap; }}
    .metric-chip {{
        background: {CARD}; border: 1px solid {BORDER}; border-radius: 8px;
        padding: 6px 14px; font-size: 0.72rem; color: {TEXT2};
    }}
    .metric-chip b {{ color: {TEXT1}; }}

    /* Multiselect, selectbox, text input, chat input */
    [data-baseweb="select"] {{
        background: {CARD} !important;
    }}
    [data-baseweb="select"] > div {{
        background: {CARD} !important; border-color: {BORDER} !important; color: {TEXT1} !important;
    }}
    [data-baseweb="popover"] > div, [data-baseweb="menu"] {{
        background: {CARD} !important; border: 1px solid {BORDER} !important;
    }}
    [data-baseweb="menu"] li {{
        background: {CARD} !important; color: {TEXT1} !important;
    }}
    [data-baseweb="menu"] li:hover {{
        background: {"#f3f4f6" if lm else "#1c1c28"} !important;
    }}
    [data-baseweb="tag"] {{
        background: {"#e5e7eb" if lm else "#2a2a3a"} !important; color: {TEXT1} !important;
    }}
    [data-baseweb="input"], [data-baseweb="textarea"], input, textarea {{
        background: {CARD} !important; color: {TEXT1} !important; border-color: {BORDER} !important;
    }}
    div[data-baseweb="base-input"] {{
        background: {CARD} !important;
    }}
    [data-testid="stChatInput"] {{
        background: {CARD} !important; border-color: {BORDER} !important;
    }}
    [data-testid="stChatInput"] textarea {{
        color: {TEXT1} !important;
    }}
    .stSlider [data-baseweb="slider"] div {{
        color: {TEXT1} !important;
    }}
    .stDataFrame {{ border: 1px solid {BORDER} !important; border-radius: 8px !important; }}
    .stMarkdown strong, .stMarkdown b {{ color: {TEXT1} !important; }}

    #MainMenu, footer {{ visibility: hidden; }}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────
defaults = {
    "pipeline_run": False, "df": None, "anomaly_report": None,
    "wealth_strategy": None, "forecast": None, "alerts": None,
    "peer_comp": None, "debate": None, "agent_metrics": None,
    "traces": {}, "timings": {}, "chat_messages": [],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def _stream(text, speed=0.012):
    for ch in text:
        yield ch
        time.sleep(speed)

# ── Header ────────────────────────────────────────────────────────
hdr_l, hdr_r = st.columns([4, 1])
with hdr_l:
    st.markdown(f"""
<div style="display:flex;align-items:baseline;gap:12px;">
    <span style="color:{TEXT1};font-size:1.85rem;font-weight:800;letter-spacing:-1.2px;">ATROPOS</span>
    <span style="background:linear-gradient(135deg,#8b5cf6,#06b6d4);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:0.72rem;font-weight:600;letter-spacing:2px;text-transform:uppercase;">FINANCE AI</span>
</div>
<div style="display:flex;align-items:center;gap:8px;margin:4px 0 0 0;">
    <span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#10b981;"></span>
    <span style="color:{TEXT3};font-size:0.78rem;">4 agents online &middot; Gemini 2.0 Flash</span>
</div>
    """, unsafe_allow_html=True)
with hdr_r:
    if st.toggle("Light mode", value=st.session_state.light_mode, key="theme_toggle"):
        if not st.session_state.light_mode:
            st.session_state.light_mode = True
            st.rerun()
    else:
        if st.session_state.light_mode:
            st.session_state.light_mode = False
            st.rerun()
st.divider()

# ── Sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ATROPOS TERMINAL")
    st.markdown("---")
    data_source = st.radio("SOURCE:", ["Upload CSV", "Demo Mode"], index=1)
    uploaded_file = None
    if data_source == "Upload CSV":
        uploaded_file = st.file_uploader("Bank statement (.csv)", type=["csv"])
    st.markdown("---")
    run_disabled = data_source == "Upload CSV" and uploaded_file is None

    if st.button("EXECUTE", type="primary", use_container_width=True, disabled=run_disabled):
        st.session_state.pipeline_run = True
        st.session_state.chat_messages = []
        reset_metrics()
        timings = {}

        if data_source == "Demo Mode":
            with st.status("loading data...", expanded=True) as status:
                t0 = time.time()
                st.write_stream(_stream("$ init mock_data --seed 42\n"))
                df = generate_mock_transactions()
                st.write_stream(_stream(f"$ {len(df)} transactions loaded\n$ range: {df['date'].min().date()} -> {df['date'].max().date()}\n$ total: INR {df['amount'].sum():,.0f}\n"))
                st.session_state.traces["data"] = f"{len(df)} txns loaded"
                timings["data"] = time.time() - t0
                status.update(label="data loaded", state="complete")
        else:
            with st.status("parsing csv...", expanded=True) as status:
                t0 = time.time()
                st.write_stream(_stream("$ reading file...\n"))
                raw_df, parse_msg = load_and_parse_csv(uploaded_file)
                st.write_stream(_stream(f"$ {parse_msg}\n"))
                if raw_df is None:
                    st.error(parse_msg); status.update(label="failed", state="error"); st.stop()
                timings["parse"] = time.time() - t0
                status.update(label="parsed", state="complete")

            with st.status("mapping columns...", expanded=True) as status:
                t0 = time.time()
                mapping, map_trace = map_columns(raw_df)
                st.write_stream(_stream(f"$ {map_trace}\n"))
                st.session_state.traces["mapper"] = map_trace
                timings["mapper"] = time.time() - t0
                status.update(label="mapped", state="complete")

            with st.status("standardizing...", expanded=True) as status:
                t0 = time.time()
                std_df, std_msg = standardize_dataframe(raw_df, mapping)
                st.write_stream(_stream(f"$ {std_msg}\n"))
                if std_df is None:
                    st.error(std_msg); status.update(label="failed", state="error"); st.stop()
                timings["standardize"] = time.time() - t0
                status.update(label="standardized", state="complete")

            with st.status("agent-1: sanitizer...", expanded=True) as status:
                t0 = time.time()
                st.write_stream(_stream("$ cleaning narrations...\n"))
                cleaned, san_trace = run_sanitizer(std_df["description"].tolist())
                st.write_stream(_stream(f"$ {san_trace}\n"))
                st.session_state.traces["sanitizer"] = san_trace
                if len(cleaned) == len(std_df):
                    std_df["merchant_name"] = [c["merchant"] for c in cleaned]
                    std_df["category"] = [c["category"] for c in cleaned]
                else:
                    std_df["merchant_name"] = std_df["description"].str[:30]
                    std_df["category"] = "Unknown"
                df = std_df
                timings["sanitizer"] = time.time() - t0
                status.update(label="sanitized", state="complete")

        with st.status("agent-2: forensic auditor...", expanded=True) as status:
            t0 = time.time()
            st.write_stream(_stream("$ scanning anomalies...\n"))
            anomaly_report, audit_trace = run_forensic_audit(df)
            st.write_stream(_stream(f"$ {audit_trace}\n"))
            st.session_state.traces["auditor"] = audit_trace
            timings["auditor"] = time.time() - t0
            status.update(label=f"{len(anomaly_report.anomalies)} anomalies", state="complete")

        with st.status("agent-3: wealth architect...", expanded=True) as status:
            t0 = time.time()
            st.write_stream(_stream("$ building action plan...\n"))
            wealth_strategy, wealth_trace = run_wealth_architect(df, anomaly_report)
            st.write_stream(_stream(f"$ {wealth_trace}\n"))
            st.session_state.traces["architect"] = wealth_trace
            timings["architect"] = time.time() - t0
            status.update(label="verdict delivered", state="complete")

        with st.status("forecasting...", expanded=True) as status:
            t0 = time.time()
            forecast = run_forecast(df)
            st.write_stream(_stream(f"$ projected: INR {forecast['projected_30d']:,.0f}\n"))
            timings["forecast"] = time.time() - t0
            status.update(label=f"INR {forecast['projected_30d']:,.0f}", state="complete")

        with st.status("agent debate...", expanded=True) as status:
            t0 = time.time()
            st.write_stream(_stream("$ synthesizing all findings...\n"))
            debate = run_agent_debate(df, anomaly_report, wealth_strategy, forecast)
            timings["debate"] = time.time() - t0
            status.update(label="consensus reached", state="complete")

        alerts = generate_smart_alerts(df, anomaly_report, wealth_strategy)
        peer_comp = get_peer_comparison(df)

        st.session_state.df = df
        st.session_state.anomaly_report = anomaly_report
        st.session_state.wealth_strategy = wealth_strategy
        st.session_state.forecast = forecast
        st.session_state.alerts = alerts
        st.session_state.peer_comp = peer_comp
        st.session_state.debate = debate
        st.session_state.timings = timings
        st.session_state.agent_metrics = get_metrics()
        st.success("Pipeline complete.")

    # Pipeline Visualizer
    if st.session_state.pipeline_run and st.session_state.timings:
        st.markdown("### AGENT PIPELINE")
        timings = st.session_state.timings
        agents_list = [("sanitizer","Sanitizer"),("auditor","Forensic Auditor"),
                       ("architect","Wealth Architect"),("forecast","Forecast"),("debate","Meta-Analyst")]
        for key, name in agents_list:
            t = timings.get(key, 0)
            st.markdown(f'<div class="pipe-step"><div class="pipe-dot pipe-done"></div>'
                        f'<span class="pipe-name">{name}</span><span class="pipe-time">{t:.1f}s</span></div>',
                        unsafe_allow_html=True)
        total_t = sum(timings.values())
        st.markdown(f'<div style="color:{"#6b7280" if lm else "#3a5a3a"};font-family:JetBrains Mono,monospace;font-size:0.68rem;margin-top:4px;">Total: {total_t:.1f}s</div>', unsafe_allow_html=True)

        # Schema Validation
        m = st.session_state.agent_metrics
        if m:
            st.markdown("---")
            st.markdown("### OBSERVABILITY")
            st.markdown(
                f'<div style="font-family:JetBrains Mono,monospace;font-size:0.68rem;color:{"#166534" if lm else "#4ade80"};line-height:1.8;">'
                f'Pydantic OK: {m["pydantic_ok"]}/{m["total_calls"]}<br>'
                f'Fallbacks: {m["fallbacks"]}<br>'
                f'Tokens in: {m["tokens_in"]:,}<br>'
                f'Tokens out: {m["tokens_out"]:,}<br>'
                f'Est. cost: ${(m["tokens_in"]*0.00001 + m["tokens_out"]*0.00004):.4f}'
                f'</div>', unsafe_allow_html=True)
        st.markdown("---")

    if st.session_state.pipeline_run and st.session_state.traces:
        st.markdown("### RUN LOG")
        for name, trace in st.session_state.traces.items():
            with st.expander(name.upper(), expanded=False):
                st.code(trace, language="bash")


# ══════════════════════════════════════════════════════════════════
# MAIN DASHBOARD
# ══════════════════════════════════════════════════════════════════
if st.session_state.pipeline_run and st.session_state.df is not None:
    df = st.session_state.df
    anomaly_report = st.session_state.anomaly_report
    wealth_strategy = st.session_state.wealth_strategy
    forecast = st.session_state.forecast
    alerts = st.session_state.alerts or []
    peer_comp = st.session_state.peer_comp or []
    debate = st.session_state.debate or ""

    # Category Filter
    all_cats = sorted(df["category"].unique().tolist())
    selected_cats = st.multiselect("Filter by category", all_cats, default=all_cats, placeholder="All categories")
    fdf = df[df["category"].isin(selected_cats)] if selected_cats else df

    # KPIs
    total_spent = fdf["amount"].sum()
    days = max((fdf["date"].max() - fdf["date"].min()).days, 1)
    daily_avg = total_spent / days
    n_txns = len(fdf)
    top_cat = fdf.groupby("category")["amount"].sum().idxmax() if len(fdf) > 0 else "-"
    top_pct = fdf.groupby("category")["amount"].sum().max() / total_spent * 100 if total_spent > 0 else 0
    n_anom = len(anomaly_report.anomalies)
    health = wealth_strategy.financial_health_score

    k1,k2,k3,k4,k5 = st.columns(5)
    with k1: st.metric("TOTAL SPENT", f"₹{total_spent:,.0f}", f"{n_txns} transactions")
    with k2: st.metric("DAILY AVG", f"₹{daily_avg:,.0f}", f"{days} days analyzed")
    with k3: st.metric("TOP CATEGORY", top_cat, f"{top_pct:.0f}% of spend")
    with k4: st.metric("ANOMALIES", str(n_anom), f"Risk {anomaly_report.risk_score:.0f}/100", delta_color="inverse" if n_anom>0 else "normal")
    with k5: st.metric("HEALTH", f"{health:.0f}/100", "Good" if health>=70 else ("Fair" if health>=50 else "Poor"), delta_color="normal" if health>=60 else "inverse")

    # Smart Alerts
    if alerts:
        st.markdown("")
        cols = st.columns(min(len(alerts), 3))
        for i, alert in enumerate(alerts[:3]):
            with cols[i]:
                st.markdown(f'<div class="alert-card alert-{alert["type"]}"><p class="alert-title">{alert["title"]}</p><p class="alert-detail">{alert["detail"]}</p></div>', unsafe_allow_html=True)
        if len(alerts) > 3:
            cols2 = st.columns(min(len(alerts)-3, 3))
            for i, alert in enumerate(alerts[3:6]):
                with cols2[i]:
                    st.markdown(f'<div class="alert-card alert-{alert["type"]}"><p class="alert-title">{alert["title"]}</p><p class="alert-detail">{alert["detail"]}</p></div>', unsafe_allow_html=True)

    st.markdown("")

    # ══════════════════════════════════════════════════════════════
    # TABS
    # ══════════════════════════════════════════════════════════════
    tab_ov, tab_an, tab_for, tab_intel, tab_sim, tab_rep = st.tabs([
        "Overview", "Deep Analysis", "Forensics", "Intelligence", "What-If Simulator", "Report & Chat",
    ])

    # ── TAB: OVERVIEW ─────────────────────────────────────────────
    with tab_ov:
        st.markdown(f'<p class="sec-title">Money Flow</p><p class="sec-sub">Account → Category → Merchant</p>', unsafe_allow_html=True)
        cat_totals = fdf.groupby("category")["amount"].sum().sort_values(ascending=False)
        top_cats = cat_totals.head(8)
        cat_cmap = {cat: P[i%len(P)] for i,cat in enumerate(top_cats.index)}

        sk_labels, sk_colors, cat_idx = ["Total"], [TEXT1], {}
        for cat in top_cats.index:
            cat_idx[cat] = len(sk_labels); sk_labels.append(cat); sk_colors.append(cat_cmap[cat])

        merch_idx, merch_cat = {}, fdf[fdf["category"].isin(top_cats.index)].groupby(["category","merchant_name"])["amount"].sum().reset_index()
        for cat in top_cats.index:
            for _, row in merch_cat[merch_cat["category"]==cat].nlargest(3,"amount").iterrows():
                key = f"{row['merchant_name']}|{cat}"
                if key not in merch_idx:
                    merch_idx[key] = len(sk_labels); sk_labels.append(row["merchant_name"]); sk_colors.append(_rgba(cat_cmap[cat],0.5))

        src,tgt,val,lcol = [],[],[],[]
        for cat,tot in top_cats.items():
            src.append(0); tgt.append(cat_idx[cat]); val.append(round(tot,2)); lcol.append(_rgba(cat_cmap[cat],0.22))
        for cat in top_cats.index:
            for _,row in merch_cat[merch_cat["category"]==cat].nlargest(3,"amount").iterrows():
                key = f"{row['merchant_name']}|{cat}"
                if key in merch_idx:
                    src.append(cat_idx[cat]); tgt.append(merch_idx[key]); val.append(round(row["amount"],2)); lcol.append(_rgba(cat_cmap[cat],0.12))

        fig_sk = go.Figure(go.Sankey(
            node=dict(pad=20,thickness=22,line=dict(color="rgba(255,255,255,0.06)",width=0.5),label=sk_labels,color=sk_colors,
                      hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}<extra></extra>"),
            link=dict(source=src,target=tgt,value=val,color=lcol,
                      hovertemplate="%{source.label} → %{target.label}<br>₹%{value:,.0f}<extra></extra>")))
        fig_sk.update_layout(**_layout(height=400,margin=dict(t=10,b=10,l=10,r=10)))
        st.plotly_chart(fig_sk, use_container_width=True)

        st.markdown("")
        c_l,c_r = st.columns(2)
        with c_l:
            st.markdown(f'<p class="sec-title">Category Split</p><p class="sec-sub">Where your money goes</p>', unsafe_allow_html=True)
            top10 = cat_totals.head(10)
            fig_dn = go.Figure(go.Pie(labels=top10.index.tolist(),values=top10.values.tolist(),hole=0.62,
                marker=dict(colors=[P[i%len(P)] for i in range(len(top10))],line=dict(color=BG,width=2)),
                textinfo="label+percent",textposition="outside",textfont=dict(size=10,color=TEXT2),
                hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}<br>%{percent}<extra></extra>",sort=False))
            fig_dn.update_layout(**_layout(height=370,margin=dict(t=10,b=10,l=10,r=10),showlegend=False,
                annotations=[dict(text=f"₹{total_spent:,.0f}",x=0.5,y=0.5,font_size=16,font_color=TEXT1,font_family="Inter",showarrow=False)]))
            st.plotly_chart(fig_dn, use_container_width=True)

        with c_r:
            st.markdown(f'<p class="sec-title">Daily Spending</p><p class="sec-sub">Trend with 7-day moving average</p>', unsafe_allow_html=True)
            daily = fdf.groupby(fdf["date"].dt.date)["amount"].sum().reset_index()
            daily.columns = ["date","amount"]; daily = daily.sort_values("date")
            daily["date"] = pd.to_datetime(daily["date"])
            daily["ma7"] = daily["amount"].rolling(7,min_periods=1).mean()
            fig_d = go.Figure()
            fig_d.add_trace(go.Bar(x=daily["date"],y=daily["amount"],name="Daily",marker_color=_rgba("#8b5cf6",0.35),hovertemplate="₹%{y:,.0f}<br>%{x|%b %d}<extra></extra>"))
            fig_d.add_trace(go.Scatter(x=daily["date"],y=daily["ma7"],name="7d avg",mode="lines",line=dict(color="#8b5cf6",width=2.5),hovertemplate="7d avg: ₹%{y:,.0f}<extra></extra>"))
            fig_d.update_layout(**_layout(height=370,showlegend=True,legend=dict(orientation="h",yanchor="bottom",y=1.02,x=0,font_size=10),
                yaxis=dict(title="₹",gridcolor=GRID,showgrid=True,zeroline=False),xaxis=dict(gridcolor=GRID,showgrid=False,zeroline=False)))
            st.plotly_chart(fig_d, use_container_width=True)

    # ── TAB: DEEP ANALYSIS ────────────────────────────────────────
    with tab_an:
        c_l2,c_r2 = st.columns(2)
        with c_l2:
            st.markdown(f'<p class="sec-title">Weekly Pattern</p><p class="sec-sub">Average spend by day of week</p>', unsafe_allow_html=True)
            dow = fdf.copy(); dow["dow"] = dow["date"].dt.dayofweek
            dow_avg = dow.groupby("dow")["amount"].mean().reindex(range(7),fill_value=0)
            dow_names = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
            fig_dow = go.Figure(go.Bar(x=dow_names,y=dow_avg.values,marker_color=[_rgba("#ef4444",0.75) if i>=5 else _rgba("#06b6d4",0.65) for i in range(7)],
                hovertemplate="<b>%{x}</b><br>₹%{y:,.0f} avg<extra></extra>"))
            fig_dow.update_layout(**_layout(height=330,yaxis=dict(title="₹ avg",gridcolor=GRID,showgrid=True,zeroline=False),xaxis=dict(gridcolor=GRID,showgrid=False,zeroline=False)))
            st.plotly_chart(fig_dow, use_container_width=True)
        with c_r2:
            st.markdown(f'<p class="sec-title">Top Merchants</p><p class="sec-sub">Biggest money sinks</p>', unsafe_allow_html=True)
            top_m = fdf.groupby("merchant_name")["amount"].sum().sort_values().tail(10)
            fig_tm = go.Figure(go.Bar(y=top_m.index,x=top_m.values,orientation="h",marker_color=[_rgba(P[i%len(P)],0.7) for i in range(len(top_m))],
                hovertemplate="<b>%{y}</b><br>₹%{x:,.0f}<extra></extra>"))
            fig_tm.update_layout(**_layout(height=330,xaxis=dict(title="₹",gridcolor=GRID,showgrid=True,zeroline=False),yaxis=dict(gridcolor=GRID,showgrid=False,zeroline=False),margin=dict(t=24,b=30,l=120,r=15)))
            st.plotly_chart(fig_tm, use_container_width=True)

        st.markdown("")
        st.markdown(f'<p class="sec-title">Spending Velocity</p><p class="sec-sub">Cumulative spend — how fast is money leaving?</p>', unsafe_allow_html=True)
        cum = daily.copy(); cum["cumulative"] = cum["amount"].cumsum()
        fig_c = go.Figure()
        fig_c.add_trace(go.Scatter(x=cum["date"],y=cum["cumulative"],mode="lines",name="Cumulative",fill="tozeroy",fillcolor=_rgba("#8b5cf6",0.08),line=dict(color="#8b5cf6",width=2.5),hovertemplate="₹%{y:,.0f}<br>%{x|%b %d}<extra></extra>"))
        fig_c.add_trace(go.Scatter(x=[cum["date"].iloc[0],cum["date"].iloc[-1]],y=[0,cum["cumulative"].iloc[-1]],mode="lines",name="Linear pace",line=dict(color="#2a2a3e",width=1.5,dash="dot"),hoverinfo="skip"))
        fig_c.update_layout(**_layout(height=280,showlegend=True,legend=dict(orientation="h",yanchor="bottom",y=1.02,x=0,font_size=10),
            yaxis=dict(title="₹ cumulative",gridcolor=GRID,showgrid=True,zeroline=False),xaxis=dict(gridcolor=GRID,showgrid=False,zeroline=False)))
        st.plotly_chart(fig_c, use_container_width=True)

        st.markdown("")
        st.markdown(f'<p class="sec-title">Month-over-Month</p><p class="sec-sub">First half vs second half by category</p>', unsafe_allow_html=True)
        mid_d = fdf["date"].min() + pd.Timedelta(days=days//2)
        h1_c = fdf[fdf["date"]<=mid_d].groupby("category")["amount"].sum()
        h2_c = fdf[fdf["date"]>mid_d].groupby("category")["amount"].sum()
        cat_ord = (h1_c.add(h2_c,fill_value=0)).sort_values(ascending=False).head(8).index.tolist()
        fig_mom = go.Figure()
        fig_mom.add_trace(go.Bar(name=f"First {days//2}d",x=cat_ord,y=[h1_c.get(c,0) for c in cat_ord],marker_color=_rgba("#06b6d4",0.6)))
        fig_mom.add_trace(go.Bar(name=f"Last {days-days//2}d",x=cat_ord,y=[h2_c.get(c,0) for c in cat_ord],marker_color=_rgba("#8b5cf6",0.6)))
        fig_mom.update_layout(**_layout(height=320,barmode="group",showlegend=True,legend=dict(orientation="h",yanchor="bottom",y=1.02,x=0,font_size=10),
            yaxis=dict(title="₹",gridcolor=GRID,showgrid=True,zeroline=False),xaxis=dict(gridcolor=GRID,showgrid=False,zeroline=False)))
        st.plotly_chart(fig_mom, use_container_width=True)

    # ── TAB: FORENSICS ────────────────────────────────────────────
    with tab_for:
        st.markdown(f'<p class="sec-title">Anomaly Timeline</p><p class="sec-sub">Flagged transactions overlaid on normal spending</p>', unsafe_allow_html=True)
        anom_ids = set()
        for a in anomaly_report.anomalies: anom_ids.update(a.transaction_indices)
        is_a = fdf.index.isin(anom_ids); norm_df = fdf[~is_a]; anom_df = fdf[is_a]
        fig_at = go.Figure()
        fig_at.add_trace(go.Scatter(x=norm_df["date"],y=norm_df["amount"],mode="markers",name="Normal",
            marker=dict(color=_rgba("#06b6d4",0.4),size=5),hovertemplate="<b>%{text}</b><br>₹%{y:,.0f}<extra></extra>",text=norm_df["merchant_name"]))
        if len(anom_df)>0:
            fig_at.add_trace(go.Scatter(x=anom_df["date"],y=anom_df["amount"],mode="markers",name="Flagged",
                marker=dict(color="#ef4444",size=13,opacity=0.9,symbol="diamond",line=dict(width=1.5,color="#fca5a5")),
                hovertemplate="<b>%{text}</b><br>₹%{y:,.0f}<extra>FLAGGED</extra>",text=anom_df["merchant_name"]))
            fig_at.add_hline(y=daily_avg*2,line_dash="dot",line_color="rgba(239,68,68,0.4)",annotation_text="2x daily avg",annotation_font_color="#ef4444",annotation_font_size=10)
        fig_at.update_layout(**_layout(height=350,legend=dict(orientation="h",yanchor="bottom",y=1.02,x=0,font_size=10),
            yaxis=dict(title="₹",gridcolor=GRID,showgrid=True,zeroline=False),xaxis=dict(gridcolor=GRID,showgrid=False,zeroline=False),hovermode="closest"))
        st.plotly_chart(fig_at, use_container_width=True)

        if anomaly_report.anomalies:
            st.markdown("")
            cf_l,cf_r = st.columns(2)
            with cf_l:
                st.markdown(f'<p class="sec-title">Anomaly Types</p>', unsafe_allow_html=True)
                at_counts = {}
                for a in anomaly_report.anomalies: t=a.anomaly_type.replace("_"," ").title(); at_counts[t]=at_counts.get(t,0)+1
                fig_atp = go.Figure(go.Pie(labels=list(at_counts.keys()),values=list(at_counts.values()),hole=0.55,
                    marker=dict(colors=[P[i%len(P)] for i in range(len(at_counts))],line=dict(color=BG,width=2)),
                    textinfo="label+value",textfont=dict(size=10,color=TEXT2)))
                fig_atp.update_layout(**_layout(height=280,margin=dict(t=10,b=10,l=10,r=10),showlegend=False))
                st.plotly_chart(fig_atp, use_container_width=True)
            with cf_r:
                st.markdown(f'<p class="sec-title">Severity Breakdown</p>', unsafe_allow_html=True)
                sv = {}; svc = {"Critical":"#ef4444","High":"#f97316","Medium":"#f59e0b","Low":"#06b6d4"}
                for a in anomaly_report.anomalies: s=a.severity.title(); sv[s]=sv.get(s,0)+1
                fig_sv = go.Figure(go.Bar(x=list(sv.keys()),y=list(sv.values()),marker_color=[svc.get(s,"#8b8b9e") for s in sv.keys()]))
                fig_sv.update_layout(**_layout(height=280,yaxis=dict(title="Count",gridcolor=GRID,showgrid=True,zeroline=False),xaxis=dict(gridcolor=GRID,showgrid=False,zeroline=False)))
                st.plotly_chart(fig_sv, use_container_width=True)

        st.markdown("")
        st.markdown(f'<p class="sec-title">Forensic Findings</p><p class="sec-sub">Each finding includes evidence transactions</p>', unsafe_allow_html=True)
        if anomaly_report.anomalies:
            sev_o = {"critical":0,"high":1,"medium":2,"low":3}
            sorted_a = sorted(anomaly_report.anomalies, key=lambda x: sev_o.get(x.severity,4))
            sev_c = {"critical":"#ef4444","high":"#f97316","medium":"#f59e0b","low":"#06b6d4"}
            conf_map = {"critical":95,"high":85,"medium":70,"low":55}
            for a in sorted_a:
                tag = {"critical":"CRIT","high":"HIGH","medium":"MED","low":"LOW"}.get(a.severity,"?")
                conf = conf_map.get(a.severity, 60)
                with st.expander(f"[{tag}] {a.title} — {conf}% confidence", expanded=(a.severity in ("critical","high"))):
                    st.markdown(f"**Type:** {a.anomaly_type.replace('_',' ').title()}")
                    st.markdown(f"**Amount:** ₹{a.amount_inr:,.2f}")
                    st.markdown(f"**Severity:** <span style='color:{sev_c.get(a.severity,'#8b8b9e')};font-weight:600;'>{a.severity.upper()}</span> &nbsp; **Confidence:** {conf}%", unsafe_allow_html=True)
                    st.markdown(a.reasoning)
                    involved = fdf.loc[fdf.index.isin(a.transaction_indices)]
                    if len(involved)>0:
                        st.markdown("**Evidence:**")
                        st.dataframe(involved[["date","merchant_name","amount","category"]].reset_index(drop=True),use_container_width=True,hide_index=True)
        else:
            st.success("No anomalies detected.")

    # ── TAB: INTELLIGENCE ─────────────────────────────────────────
    with tab_intel:
        # Agent Debate
        st.markdown(f'<p class="sec-title">Agent Consensus</p><p class="sec-sub">Meta-analysis: all agents debate their findings</p>', unsafe_allow_html=True)
        st.markdown(f'<div style="background:{CARD};border:1px solid {BORDER};border-radius:10px;padding:20px;">', unsafe_allow_html=True)
        st.markdown(debate)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("")
        st.divider()

        # Forecast
        if forecast:
            fc1,fc2,fc3 = st.columns(3)
            with fc1: st.metric("30-DAY PROJECTION",f"₹{forecast['projected_30d']:,.0f}",f"{'↑' if forecast['trend_pct']>0 else '↓'} {abs(forecast['trend_pct']):.1f}%",delta_color="inverse" if forecast["trend_pct"]>5 else "normal")
            with fc2: st.metric("DAILY BURN RATE",f"₹{forecast['daily_rate']:,.0f}","per day")
            with fc3: st.metric("ANNUAL ESTIMATE",f"₹{forecast['daily_rate']*365:,.0f}","at current pace")

            st.markdown("")
            st.markdown(f'<p class="sec-title">Category Forecast</p><p class="sec-sub">Projected 30-day spend vs current</p>', unsafe_allow_html=True)
            cp = forecast["category_projections"]
            cs = sorted(cp.keys(),key=lambda c:cp[c]["projected_30d"],reverse=True)[:10]
            fig_fc = go.Figure()
            fig_fc.add_trace(go.Bar(name="Current",x=cs,y=[cp[c]["current_total"] for c in cs],marker_color=_rgba("#06b6d4",0.5)))
            fig_fc.add_trace(go.Bar(name="30d Projected",x=cs,y=[cp[c]["projected_30d"] for c in cs],marker_color=_rgba("#f59e0b",0.6)))
            fig_fc.update_layout(**_layout(height=350,barmode="group",showlegend=True,legend=dict(orientation="h",yanchor="bottom",y=1.02,x=0,font_size=10),
                yaxis=dict(title="₹",gridcolor=GRID,showgrid=True,zeroline=False),xaxis=dict(gridcolor=GRID,showgrid=False,zeroline=False)))
            st.plotly_chart(fig_fc, use_container_width=True)

        st.markdown("")
        st.divider()

        # Peer Benchmarks
        st.markdown(f'<p class="sec-title">Peer Benchmarking</p><p class="sec-sub">Your spending vs Indian urban household averages</p>', unsafe_allow_html=True)
        if peer_comp:
            for comp in peer_comp[:8]:
                cat,user_pct,bench_pct,ratio,status = comp["category"],comp["user_pct"],comp["benchmark_pct"],comp["ratio"],comp["status"]
                bar_col = "#ef4444" if status=="over" else ("#10b981" if status=="under" else "#8b5cf6")
                mx = max(user_pct,bench_pct,1)
                st.markdown(f'''<div style="margin-bottom:10px;">
<div style="display:flex;justify-content:space-between;margin-bottom:3px;"><span style="color:{TEXT1};font-size:0.8rem;font-weight:600;">{cat}</span><span style="color:{TEXT3};font-size:0.68rem;">{ratio:.1f}x {"above" if status=="over" else ("below" if status=="under" else "at")} avg</span></div>
<div style="position:relative;height:20px;background:{BORDER};border-radius:4px;overflow:hidden;"><div style="position:absolute;height:100%;width:{min(user_pct/mx*100,100)}%;background:{_rgba(bar_col,0.5)};border-radius:4px;"></div><div style="position:absolute;height:100%;width:2px;left:{min(bench_pct/mx*100,100)}%;background:#ffffff44;"></div></div>
<div style="display:flex;justify-content:space-between;margin-top:2px;"><span style="color:{TEXT2};font-size:0.65rem;">You: {user_pct:.1f}%</span><span style="color:{TEXT3};font-size:0.65rem;">Avg: {bench_pct}%</span></div></div>''', unsafe_allow_html=True)

        # Email Alert Simulation
        st.markdown("")
        st.divider()
        st.markdown(f'<p class="sec-title">Daily Alert Preview</p><p class="sec-sub">What your morning notification would look like</p>', unsafe_allow_html=True)
        top_findings = [a.title for a in anomaly_report.anomalies[:3]]
        action = wealth_strategy.action_plan[0].title if wealth_strategy.action_plan else "Review spending"
        st.markdown(f'''<div style="background:{"#fff" if lm else "#1a1a24"};border:1px solid {BORDER};border-radius:10px;padding:20px;max-width:500px;">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;"><div style="width:28px;height:28px;background:#8b5cf6;border-radius:6px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:0.7rem;">A</div><span style="color:{TEXT1};font-weight:600;font-size:0.85rem;">ATROPOS Daily Briefing</span><span style="color:{TEXT3};font-size:0.68rem;margin-left:auto;">Today</span></div>
<p style="color:{TEXT1};font-size:0.82rem;font-weight:500;margin:0 0 8px 0;">Good morning! Here's your financial pulse:</p>
<ul style="color:{TEXT2};font-size:0.78rem;margin:0;padding-left:18px;line-height:1.8;">
{"".join(f'<li>{f}</li>' for f in top_findings) if top_findings else '<li>No critical issues today</li>'}
</ul>
<p style="color:{TEXT1};font-size:0.78rem;font-weight:500;margin:12px 0 4px 0;">Priority Action: <span style="color:#8b5cf6;">{action}</span></p>
<p style="color:{TEXT3};font-size:0.68rem;margin:8px 0 0 0;">Score: {health:.0f}/100 | Risk: {anomaly_report.risk_score:.0f}/100</p>
</div>''', unsafe_allow_html=True)

    # ── TAB: WHAT-IF SIMULATOR ────────────────────────────────────
    with tab_sim:
        st.markdown(f'<p class="sec-title">What-If Simulator</p><p class="sec-sub">Drag sliders to model spending reductions per category and instantly see projected savings</p>', unsafe_allow_html=True)
        st.info("Each slider reduces that category's spending by the chosen %. For example, setting Food Delivery to 30% means you'd spend 30% less on food delivery. The savings are projected to monthly and annual totals.", icon="💡")
        cat_spend = fdf.groupby("category")["amount"].sum().sort_values(ascending=False)
        top_sim_cats = cat_spend.head(8)

        adjustments = {}
        sim_cols = st.columns(2)
        for i, (cat, amt) in enumerate(top_sim_cats.items()):
            with sim_cols[i % 2]:
                monthly_amt = amt / days * 30
                pct = st.slider(f"{cat} — ₹{monthly_amt:,.0f}/mo", min_value=0, max_value=100, value=0, step=5, key=f"sim_{cat}", format="%d%% cut")
                if pct > 0:
                    st.caption(f"Saves ₹{monthly_amt * pct / 100:,.0f}/mo")
                adjustments[cat] = pct

        total_savings = sum(top_sim_cats[cat] * pct / 100 for cat, pct in adjustments.items())
        monthly_proj = (total_spent - total_savings) / days * 30
        annual_proj = monthly_proj * 12

        st.markdown("")
        s1,s2,s3 = st.columns(3)
        with s1: st.metric("MONTHLY SAVINGS", f"₹{total_savings/days*30:,.0f}", f"from {sum(1 for v in adjustments.values() if v>0)} categories")
        with s2: st.metric("NEW MONTHLY SPEND", f"₹{monthly_proj:,.0f}", f"vs ₹{total_spent/days*30:,.0f}")
        with s3: st.metric("ANNUAL SAVINGS", f"₹{total_savings/days*365:,.0f}", "projected")

        st.markdown("")
        # Visualization
        fig_sim = go.Figure()
        cats_sim = list(top_sim_cats.index)
        orig_vals = [top_sim_cats[c] for c in cats_sim]
        new_vals = [top_sim_cats[c] * (1 - adjustments.get(c, 0) / 100) for c in cats_sim]
        fig_sim.add_trace(go.Bar(name="Current", x=cats_sim, y=orig_vals, marker_color=_rgba("#ef4444", 0.4)))
        fig_sim.add_trace(go.Bar(name="After Cuts", x=cats_sim, y=new_vals, marker_color=_rgba("#10b981", 0.6)))
        fig_sim.update_layout(**_layout(height=350, barmode="group", showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font_size=10),
            yaxis=dict(title="₹", gridcolor=GRID, showgrid=True, zeroline=False),
            xaxis=dict(gridcolor=GRID, showgrid=False, zeroline=False)))
        st.plotly_chart(fig_sim, use_container_width=True)

    # ── TAB: REPORT & CHAT ────────────────────────────────────────
    with tab_rep:
        # Audio Summary
        audio_text = (f"Your total spending over {days} days is {total_spent:,.0f} rupees across {n_txns} transactions. "
                      f"The top category is {top_cat} at {top_pct:.0f} percent. "
                      f"{n_anom} anomalies detected, risk score {anomaly_report.risk_score:.0f} out of 100. "
                      f"Health score is {health:.0f} out of 100. ")
        if forecast: audio_text += f"Projected 30 day spend: {forecast['projected_30d']:,.0f} rupees. "
        if wealth_strategy.action_plan:
            ts = sum(s.estimated_monthly_savings for s in wealth_strategy.action_plan)
            audio_text += f"Potential monthly savings: {ts:,.0f} rupees."
        audio_js = audio_text.replace("'", "\\'").replace("\n", " ")
        components.html(f'''<div style="background:{CARD};border:1px solid {BORDER};border-radius:10px;padding:16px 20px;font-family:Inter,-apple-system,sans-serif;">
<div style="display:flex;align-items:center;justify-content:space-between;">
<div><p style="color:{TEXT1};font-weight:600;font-size:0.88rem;margin:0;">Executive Briefing</p>
<p style="color:{TEXT3};font-size:0.72rem;margin:3px 0 0 0;">AI-generated audio summary</p></div>
<button id="playBtn" style="background:#8b5cf6;color:#fff;border:none;border-radius:8px;padding:8px 20px;font-weight:600;font-size:0.78rem;cursor:pointer;font-family:Inter,sans-serif;">Play Summary</button>
</div></div>
<script>
document.getElementById('playBtn').addEventListener('click', function() {{
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance('{audio_js}');
    u.rate = 0.95;
    this.textContent = 'Playing...';
    const btn = this;
    u.onend = function() {{ btn.textContent = 'Play Summary'; }};
    window.speechSynthesis.speak(u);
}});
</script>''', height=80)

        # Downloads
        st.markdown(f'<p class="sec-title">Download Reports</p>', unsafe_allow_html=True)
        dl1,dl2,dl3 = st.columns(3)
        with dl1:
            pdf_bytes = generate_pdf_report(df, anomaly_report, wealth_strategy, forecast)
            st.download_button("Download PDF", pdf_bytes, file_name="atropos_report.pdf", mime="application/pdf", use_container_width=True)
        with dl2:
            sorted_a = sorted(anomaly_report.anomalies, key=lambda x: {"critical":0,"high":1,"medium":2,"low":3}.get(x.severity,4))
            lines = ["ATROPOS FORENSIC REPORT", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", f"Risk: {anomaly_report.risk_score}/100", "", anomaly_report.summary, ""]
            for i,a in enumerate(sorted_a,1): lines += [f"[{i}] [{a.severity.upper()}] {a.title}", f"  Amount: INR {a.amount_inr:,.2f}", f"  {a.reasoning}", ""]
            st.download_button("Download TXT", "\n".join(lines), file_name="atropos_report.txt", mime="text/plain", use_container_width=True)
        with dl3:
            csv_d = pd.DataFrame([{"Severity":a.severity,"Title":a.title,"Type":a.anomaly_type,"Amount":a.amount_inr,"Reasoning":a.reasoning} for a in sorted_a]).to_csv(index=False)
            st.download_button("Download CSV", csv_d, file_name="atropos_report.csv", mime="text/csv", use_container_width=True)

        st.divider()
        rep_l,rep_r = st.columns(2)
        with rep_l:
            st.markdown("### Forensic Summary")
            st.markdown(anomaly_report.summary)
            st.markdown(f"**Risk:** {anomaly_report.risk_score:.0f}/100 | **Anomalies:** {len(anomaly_report.anomalies)}")
        with rep_r:
            st.markdown("### Action Plan")
            if wealth_strategy.action_plan:
                ts = sum(s.estimated_monthly_savings for s in wealth_strategy.action_plan)
                st.markdown(f"**Potential savings: ₹{ts:,.0f}/month**")
                for step in wealth_strategy.action_plan:
                    with st.expander(f"Step {step.step_number}: {step.title}", expanded=True):
                        st.markdown(step.description)
                        st.metric("Monthly Savings", f"₹{step.estimated_monthly_savings:,.0f}")
            st.markdown("---")
            st.markdown(f"**Verdict:** {wealth_strategy.overall_verdict}")

        st.divider()

        # Transaction Explorer
        st.markdown(f'<p class="sec-title">Transaction Explorer</p><p class="sec-sub">Search and drill into individual transactions</p>', unsafe_allow_html=True)
        search = st.text_input("Search transactions", placeholder="e.g. Swiggy, Netflix, hidden fee...")
        show_df = fdf[["date","merchant_name","amount","category"]].copy()
        show_df["date"] = show_df["date"].dt.strftime("%Y-%m-%d")
        show_df["Flagged"] = np.where(fdf.index.isin(anom_ids), "Yes", "")
        if search:
            mask = show_df.apply(lambda r: search.lower() in str(r).lower(), axis=1)
            show_df = show_df[mask]
        st.dataframe(show_df.reset_index(drop=True), use_container_width=True, hide_index=True, height=350)

        st.divider()

        # Chat
        st.markdown(f'<p class="sec-title">Ask your data anything</p><p class="sec-sub">Natural language Q&A powered by Gemini</p>', unsafe_allow_html=True)
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        if prompt := st.chat_input("e.g. How much did I spend on Swiggy?"):
            st.session_state.chat_messages.append({"role":"user","content":prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."): resp = chat_with_data(df, prompt, st.session_state.chat_messages)
                st.markdown(resp)
            st.session_state.chat_messages.append({"role":"assistant","content":resp})


else:
    # ══════════════════════════════════════════════════════════════
    # LANDING
    # ══════════════════════════════════════════════════════════════
    st.markdown("")
    _,center,_ = st.columns([1,3,1])
    with center:
        st.markdown(f"""
<div style="text-align:center;padding:40px 0 20px 0;">
    <p style="color:#8b5cf6;font-size:3rem;font-weight:800;letter-spacing:-2px;margin:0;">ATROPOS</p>
    <p style="color:{TEXT3};font-size:0.95rem;margin:8px 0 30px 0;">Multi-agent financial intelligence. Upload any bank CSV.</p>
</div>""", unsafe_allow_html=True)

        cards = [
            ("01","#8b5cf6","Sanitizer","Cleans messy bank narrations into structured merchant + category data."),
            ("02","#ef4444","Forensic Auditor","Hunts subscription creep, hidden fees, weekend inflation, duplicates, spikes."),
            ("03","#10b981","Wealth Architect","Builds a brutal 3-step savings plan with exact INR amounts from your data."),
        ]
        cols = st.columns(3)
        for i,(num,col,name,desc) in enumerate(cards):
            with cols[i]:
                st.markdown(f'''<div style="background:{CARD};border:1px solid {BORDER};border-radius:12px;padding:24px 18px;text-align:center;min-height:200px;">
<p style="color:{col};font-size:1.6rem;font-weight:700;margin:0;">{num}</p>
<p style="color:{TEXT1};font-size:0.92rem;font-weight:600;margin:8px 0 6px 0;">{name}</p>
<p style="color:{TEXT3};font-size:0.78rem;line-height:1.5;margin:0;">{desc}</p></div>''', unsafe_allow_html=True)

        st.markdown("")
        cards2 = [
            ("04","#f59e0b","Forecast Engine","30-day spending projection per category with trend analysis."),
            ("05","#06b6d4","Agent Debate","Meta-analysis: all agents synthesize findings into unified brief."),
            ("06","#ec4899","What-If Simulator","Model spending cuts and see projected savings instantly."),
        ]
        cols2 = st.columns(3)
        for i,(num,col,name,desc) in enumerate(cards2):
            with cols2[i]:
                st.markdown(f'''<div style="background:{CARD};border:1px solid {BORDER};border-radius:12px;padding:24px 18px;text-align:center;min-height:200px;">
<p style="color:{col};font-size:1.6rem;font-weight:700;margin:0;">{num}</p>
<p style="color:{TEXT1};font-size:0.92rem;font-weight:600;margin:8px 0 6px 0;">{name}</p>
<p style="color:{TEXT3};font-size:0.78rem;line-height:1.5;margin:0;">{desc}</p></div>''', unsafe_allow_html=True)

        st.markdown(f'''<div style="text-align:center;padding:30px 0 0 0;">
<p style="color:{TEXT3};font-size:0.78rem;">Select a data source and hit <span style="color:#8b5cf6;font-weight:600;">EXECUTE</span> in the sidebar.</p>
<p style="color:{"#d0d5dd" if lm else "#2a2a38"};font-size:0.68rem;margin-top:4px;">Supports HDFC, SBI, ICICI, Kotak, Axis — any standard CSV format.</p>
</div>''', unsafe_allow_html=True)
