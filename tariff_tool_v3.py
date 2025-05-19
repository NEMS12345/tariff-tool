import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import re
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Try to load environment variables from .env file for local development
try:
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)
        print(f"Found .env file at: {env_path}")
except Exception as e:
    print(f"Error loading .env file: {e}")

# ───────────────────────────────────────────────────────────────
# CONFIGURATION
# ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Tariff Tool",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Debug information about environment
try:
    if os.path.exists(os.path.join(os.path.dirname(__file__), '.env')):
        st.sidebar.success("Found .env file for local development")
    elif 'supabase' in st.secrets:
        st.sidebar.success("Found Streamlit secrets configuration")
    else:
        st.sidebar.warning("No configuration found. Using fallback values.")
except Exception as e:
    st.sidebar.error(f"Error checking configuration: {e}")

# ───────────────────────────────────────────────────────────────
# GLOBAL CSS
# ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
        html, body { font-size: 100% !important; }
        div.block-container { padding: 0.5rem !important; }
        .element-container { margin: 0.2rem 0 !important; }
        /* Metric tiles */
        div[data-testid="metric-container"]{
            background:#f8f9fa;border:1px solid #dee2e6;
            border-radius:0.5rem;padding:1rem;text-align:center;
            margin-bottom:0.5rem;width:100%;
        }
        div[data-testid="metric-container"]>div{justify-content:center;}
        div[data-testid="metric-container"] label{font-size:1.2rem !important;}
        div[data-testid="metric-container"] div[data-testid="metric-value"]{
            font-size:2rem !important;
        }
        /* Headings */
        h1,h2,h3,h4,.stMarkdown h1,.stMarkdown h2{
            color:#000;font-size:1.5rem;margin:0.5rem 0;
        }
        /* Tables */
        .stTable table th,.stTable table td,
        .stDataFrame table th,.stDataFrame table td{
            font-size:1rem;padding:0.3rem;white-space:nowrap;
        }
        .stTable{margin:0.5rem 0;}
        .stMarkdown p,.stMarkdown li{font-size:1.2rem;}
        button[role="tab"]{font-size:1.2rem;font-weight:bold;}
        .stTabs [data-baseweb="tab-panel"]{padding-top:0.5rem;padding-bottom:1rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ───────────────────────────────────────────────────────────────
# SUPABASE INITIALISATION
# ───────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def supabase_client() -> Client:
    # Try to get from Streamlit secrets first (for cloud deployment)
    try:
        if 'supabase' in st.secrets:
            url = st.secrets.supabase.url
            key = st.secrets.supabase.key
            st.sidebar.success("Using Streamlit secrets for Supabase credentials")
            return create_client(url, key)
    except Exception as e:
        st.sidebar.error(f"Error accessing Streamlit secrets: {e}")
    
    # Try to get from environment variables (for local development)
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    # Debug information
    st.sidebar.markdown("### Credentials Debug")
    st.sidebar.write(f"SUPABASE_URL found: {'Yes' if url else 'No'}")
    st.sidebar.write(f"SUPABASE_KEY found: {'Yes' if key else 'No'}")
    
    # Use hardcoded values as fallback
    if not url:
        url = "https://nivriefipgzsqexdnhaa.supabase.co"
        st.sidebar.warning("Using hardcoded URL as fallback")
    
    if not key:
        key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5pdnJpZWZpcGd6c3FleGRuaGFhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY4NTIyMDEsImV4cCI6MjA2MjQyODIwMX0.trAUIqGoZ2fOOu8C1CUlhnvNDFpRt7CIH4SxPegP1Ag"
        st.sidebar.warning("Using hardcoded key as fallback")
    
    return create_client(url, key)

client = supabase_client()

# ───────────────────────────────────────────────────────────────
# HELPERS
# ───────────────────────────────────────────────────────────────
DAYS = 365
money   = lambda x: f"${x:,.0f}"
sfloat  = lambda x, d=0.0: float(x) if (isinstance(x, (int, float)) or str(x).replace('.', '', 1).isdigit()) else d

# ───────────────────────────────────────────────────────────────
# SIDEBAR
# ───────────────────────────────────────────────────────────────
villages = sorted(r["village_name"].strip()
                  for r in client.table("village_inputs").select("village_name").execute().data)
# Add a summary option at the top of the dropdown
villages = ["Summary of All Villages"] + villages
sel = st.sidebar.selectbox("Select Village", villages)

usage_rate_sim = st.sidebar.number_input("Simulation Usage Rate (c/kWh)", 0.0, 100.0, 20.0, 0.01)
daily_sim      = st.sidebar.number_input("Simulation Daily Supply ($/day)", 0.0, 5.0, 1.0, 0.0001)

# AWS Fee Toggle
st.sidebar.markdown("---")
include_aws_fee = st.sidebar.checkbox("Include AWS Fee", value=True, help="Toggle to include or exclude the AWS Service Fee from calculations")

# ───────────────────────────────────────────────────────────────
# VILLAGE DATA LOADING
# ───────────────────────────────────────────────────────────────
is_summary = sel == "Summary of All Villages"

if is_summary:
    # Load data for all villages
    all_villages_data = client.table("village_inputs").select("*").execute().data
    all_tariffs = client.table("en_tariffs").select("village_name,_usage,_supply").execute().data
    
    # Initialize aggregated values
    res_kwh = com_kwh = res_supply = com_supply = 0.0
    site_kwh = qty_total = village_total_cost = 0.0
    nmi_total = 0
    
    # Calculate average rates from all villages with tariffs
    valid_tariffs = [t for t in all_tariffs if t.get("_usage") and t.get("_supply")]
    if valid_tariffs:
        avg_u_rate = sum(sfloat(t["_usage"]) for t in valid_tariffs) / len(valid_tariffs)
        avg_d_daily = sum(sfloat(t["_supply"]) / 100 for t in valid_tariffs) / len(valid_tariffs)
        village_u_rate = avg_u_rate
        village_d_daily = avg_d_daily
    else:
        village_u_rate = usage_rate_sim
        village_d_daily = daily_sim
        st.warning("No stored tariffs found — using sidebar values for rates.")
    
    # Aggregate data from all villages
    for row in all_villages_data:
        # Sum up usage and supply values
        for col, val in row.items():
            m = re.match(r"q[1-4]_(usage|supply)_(res|common)", col.lower())
            if not m: continue
            kind, area = m.groups()
            v = sfloat(val)
            if area == "res":
                res_kwh += v if kind == "usage" else 0
                res_supply += v if kind == "supply" else 0
            else:
                com_kwh += v if kind == "usage" else 0
                com_supply += v if kind == "supply" else 0
        
        # Add to totals
        site_kwh += sfloat(row.get("total_usage_kwh", 0))
        nmi_total += int(sfloat(row.get("nmis_res", 0))) + int(sfloat(row.get("nmis_common", 0)))
        village_total_cost += sfloat(row.get("total_cost", 0))
    
    # If site_kwh is zero, use the sum of res_kwh and com_kwh
    if site_kwh == 0:
        site_kwh = res_kwh + com_kwh
    
    qty_total = res_kwh + com_kwh
    
    # Display summary info
    st.info(f"Showing aggregated data for {len(all_villages_data)} villages")
    
else:
    # Original code for single village
    tar = (client.table("en_tariffs")
                .select("village_name,_usage,_supply")
                .eq("village_name", sel)
                .execute()
                .data)
    if tar and tar[0].get("_usage") and tar[0].get("_supply"):
        village_u_rate  = sfloat(tar[0]["_usage"])          # c/kWh
        village_d_daily = sfloat(tar[0]["_supply"]) / 100   # $/day
    else:
        st.warning(f"No stored tariff for **{sel}** — using sidebar values.")
        village_u_rate  = usage_rate_sim
        village_d_daily = daily_sim

    # ───────────────────────────────────────────────────────────────
    # VILLAGE INPUTS
    # ───────────────────────────────────────────────────────────────
    row = (client.table("village_inputs").select("*").eq("village_name", sel).execute().data[0])

    res_kwh = com_kwh = res_supply = com_supply = 0.0
    for col, val in row.items():
        m = re.match(r"q[1-4]_(usage|supply)_(res|common)", col.lower())
        if not m: continue
        kind, area = m.groups()
        v = sfloat(val)
        if area == "res":
            res_kwh    += v if kind == "usage" else 0
            res_supply += v if kind == "supply" else 0
        else:
            com_kwh    += v if kind == "usage" else 0
            com_supply += v if kind == "supply" else 0

    site_kwh           = sfloat(row.get("total_usage_kwh")) or (res_kwh + com_kwh)
    nmi_total          = int(sfloat(row.get("nmis_res"))) + int(sfloat(row.get("nmis_common")))
    qty_total          = res_kwh + com_kwh
    village_total_cost = sfloat(row.get("total_cost"))

# ───────────────────────────────────────────────────────────────
# CONSTANTS
# ───────────────────────────────────────────────────────────────
aws_revenue = 56_880        # fixed p.a.
seene_costs = 54_360        # fixed platform cost

# ───────────────────────────────────────────────────────────────
# CURRENT & SIMULATED REVENUES
# ───────────────────────────────────────────────────────────────
# Apply AWS fee toggle
applied_aws_revenue = aws_revenue if include_aws_fee else 0

# Current
current_usage_rev   = qty_total * village_u_rate  / 100
current_supply_rev  = res_supply + com_supply
current_total_rev   = current_usage_rev + current_supply_rev + applied_aws_revenue
current_opex        = (
    village_total_cost +
    seene_costs -
    (current_usage_rev + current_supply_rev + applied_aws_revenue)
)

# Simulated
sim_usage_rev       = qty_total * usage_rate_sim / 100
sim_supply_rev      = nmi_total * daily_sim * DAYS
rate_diff_pct       = usage_rate_sim / village_u_rate if village_u_rate else 1
sim_aws_revenue     = applied_aws_revenue * rate_diff_pct
sim_total_rev       = sim_usage_rev + sim_supply_rev + sim_aws_revenue
sim_opex            = (
    village_total_cost +
    seene_costs -
    (sim_usage_rev + sim_supply_rev + sim_aws_revenue)
)
# ───────────────────────────────────────────────────────────────
# LOGO + PAGE TITLE  (insert right before st.title)
# ───────────────────────────────────────────────────────────────
import os

# Use a relative path for the logo file that works in both local and cloud environments
try:
    # Try to use the logo file in the current directory
    logo_path = "logo.jpg"
    
    # Skip logo if running in cloud and file doesn't exist
    if not os.path.exists(logo_path):
        st.sidebar.warning("Logo file not found. Skipping logo display.")
        has_logo = False
    else:
        has_logo = True
except Exception as e:
    st.sidebar.error(f"Error loading logo: {e}")
    has_logo = False

col_logo, col_title = st.columns([9, 9])   # 1/10 width for the logo, 9/10 for title
with col_logo:
    if has_logo:
        st.image(logo_path, width=300)          # tweak width if you need larger/smaller
with col_title:
    if is_summary:
        st.title("All Villages Summary - Embedded Network Review 2024")
    else:
        st.title(f"{sel} Embedded Network Review 2024")

#
# ───────────────────────────────────────────────────────────────
# TABS
# ───────────────────────────────────────────────────────────────
tab_overview, tab_wholesale, tab_opex, tab_notes = st.tabs(
    ["💡 Overview", "📈 Energy Market Pricing", "📉 Village Operation", "📝 Consultant Notes"]
)

# =================================================================
# TAB 1 — OVERVIEW
# =================================================================
with tab_overview:
    c_met, c_pie = st.columns([4, 6])
    # ── Metrics
    with c_met:
        # Define metrics based on AWS fee toggle
        if include_aws_fee:
            metrics = [
                ("Usage Revenue - Billed via monthly Seene invoices at 22.11c/kWh ", current_usage_rev),
                ("Supply Revenue - Billed via monthly Seene invoices at $1.073/Day", current_supply_rev),
                ("AWS Revenue - BIlled via Monthly Service Fee", applied_aws_revenue),
                ("Total Revenue (ex GST)", current_total_rev),
            ]
        else:
            metrics = [
                ("Usage Revenue - Billed via monthly Seene invoices at 22.11c/kWh ", current_usage_rev),
                ("Supply Revenue - Billed via monthly Seene invoices at $1.073/Day", current_supply_rev),
                ("Total Revenue (ex GST)", current_total_rev),
            ]
        for label, val in metrics:
            st.metric(label, money(val))

    # ── Pie chart
    with c_pie:
        aws_equiv_kwh = applied_aws_revenue / (village_u_rate / 100) if village_u_rate and include_aws_fee else 0
        other_kwh     = max(site_kwh - res_kwh, 0.0)
        fig, ax = plt.subplots(figsize=(3.5, 3.5))
        # Prepare data for pie chart based on AWS fee toggle
        if include_aws_fee:
            pie_data = [res_kwh, other_kwh, aws_equiv_kwh]
            pie_colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
            pie_labels = ["Metered Residential", "Metered Village", "AWS Fees"]
        else:
            pie_data = [res_kwh, other_kwh]
            pie_colors = ["#1f77b4", "#ff7f0e"]
            pie_labels = ["Metered Residential", "Metered Village"]
            
        ax.pie(
            pie_data,
            labels=None,
            autopct="%1.1f%%",
            startangle=90,
            textprops={"fontsize": 14},
            colors=pie_colors,
        )
        ax.axis("equal")
        ax.legend(pie_labels, loc="center left", bbox_to_anchor=(1, 0.5))
        st.pyplot(fig)

    # ─────────────────────────────────────────────────────────
    # COMPETITOR PRICE COMPARISON  (restored)
    # ─────────────────────────────────────────────────────────
    st.markdown("### On-Market Price Comparison")

    # Skip competitor comparison in summary view
    if is_summary:
        st.info("Competitor price comparison is not available in summary view. Please select a specific village to see competitor comparisons.")
    # Only run if a stored tariff exists (otherwise we don't know the village rate)
    elif village_u_rate and village_d_daily:

        # Map column names in competitor_offers
        retailers = {
            "agl":      ("AGL",      "agl_usage_rate",      "agl_daily_charge"),
            "ea":       ("EnergyAus","ea_usage_rate",       "ea_daily_charge"),
            "origin":   ("Origin",   "origin_usage_rate",   "origin_daily_charge"),
            "alinta":   ("Alinta",   "alinta_usage_rate",   "alinta_daily_charge"),
            "momentum": ("Momentum", "momentum_usage_rate", "momentum_daily_charge"),
            "actewagl": ("ActewAGL", "actewagl_usage_rate", "actewagl_daily_charge"),
        }

        comp_raw = (
            client.table("competitor_offers")
                  .select("*")
                  .eq("village_name", sel)
                  .execute()
                  .data
        )
        comp_raw = comp_raw[0] if comp_raw else {}

        def tot_cost(u, d):
            usage  = qty_total * u / 100
            supply = nmi_total * d * DAYS
            return usage, supply, usage + supply

        # Village row first
        v_usage  = current_usage_rev
        v_supply = current_supply_rev
        v_total  = current_total_rev
        rows = [{
            "Provider":                "Village",
            "Usage rate (c/kWh)":      f"{village_u_rate:.2f}",
            "Daily charge ($/day)":    f"{village_d_daily:.4f}",
            "Total Usage $":           money(v_usage),
            "Total Supply $":          money(v_supply),
            "Total Cost $":            money(v_total),
            "Δ vs Village %":          "0.0%",
        }]

        # Competitors
        for lbl, u_key, d_key in retailers.values():
            if comp_raw.get(u_key) and comp_raw.get(d_key):
                u  = sfloat(comp_raw[u_key])
                d  = sfloat(comp_raw[d_key]) / 100     # stored as ¢/day
                c_u, c_s, c_t = tot_cost(u, d)
                delta = (c_t - v_total) / v_total * 100
                rows.append({
                    "Provider":                lbl,
                    "Usage rate (c/kWh)":      f"{u:.2f}",
                    "Daily charge ($/day)":    f"{d:.4f}",
                    "Total Usage $":           money(c_u),
                    "Total Supply $":          money(c_s),
                    "Total Cost $":            money(c_t),
                    "Δ vs Village %":          f"{delta:+.1f}%",
                })

        # Move the village row to the bottom so it's easy to compare
        village_row     = rows.pop(0)
        rows.append(village_row)

        comp_df = (pd.DataFrame(rows)
                     .set_index("Provider")[[  # keep column order tidy
                         "Usage rate (c/kWh)",
                         "Daily charge ($/day)",
                         "Total Usage $",
                         "Total Supply $",
                         "Total Cost $",
                         "Δ vs Village %",
                      ]])

        # Simple highlight: red if > 1 % dearer, green if cheaper
        def colour_delta(val):
            try:
                pct = float(str(val).replace('%', ''))
                if pct > 1:   return "background-color:#f8d7da;color:#721c24"
                if pct < -1:  return "background-color:#d4edda;color:#155724"
            except: pass
            return ""

        st.dataframe(
            comp_df.style.applymap(colour_delta, subset=["Δ vs Village %"]),
            hide_index=False,
            use_container_width=True,
            height=len(comp_df)*50+3,
        )
    else:
        st.info("Add `_usage` & `_supply` to `en_tariffs` to enable competitor comparison.")

# =================================================================
# TAB 2 — VILLAGE OPEX  (vertical layout)
# =================================================================
with tab_opex:
    # ── (A) Waterfall Chart ────────────────────────────────────
    st.markdown("### Village OPEX Waterfall")
    
    # Define steps based on AWS fee toggle
    if include_aws_fee:
        steps = [
            ("Total Cost",          -village_total_cost),
            ("Seene Costs",         -seene_costs),
            ("Usage Revenue",        current_usage_rev),
            ("Supply Revenue",       current_supply_rev),
            ("AWS Service Fee",      applied_aws_revenue),
            ("OPEX Budget",          current_opex),
        ]
        colors = ["#d9534f", "#d9534f", "#28a745", "#28a745", "#28a745", "#fd7e14"]
    else:
        steps = [
            ("Total Cost",          -village_total_cost),
            ("Seene Costs",         -seene_costs),
            ("Usage Revenue",        current_usage_rev),
            ("Supply Revenue",       current_supply_rev),
            ("OPEX Budget",          current_opex),
        ]
        colors = ["#d9534f", "#d9534f", "#28a745", "#28a745", "#fd7e14"]
    
    cum = [0]
    for v in [v for _, v in steps[:-1]]:
        cum.append(cum[-1] + v)
    fig2, ax2 = plt.subplots(figsize=(6, 4))
    for i, (lbl, val) in enumerate(steps):
        ax2.bar(lbl, val, bottom=cum[i], color=colors[i], width=0.8)
    ax2.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, pos: f'${x:,.0f}')
    )
    ax2.grid(axis="y", alpha=0.3)
    plt.xticks(rotation=90)
    st.pyplot(fig2)

    # ── (B) Summary Table with formulas & colours ──────────────
    st.markdown("### Village OPEX Summary")

    # Define summary table data based on AWS fee toggle
    if include_aws_fee:
        numbers_current = {
            "Total Cost"     : village_total_cost,
            "Seene Costs"    : seene_costs,
            "Usage Revenue"  : current_usage_rev,
            "Supply Revenue" : current_supply_rev,
            "AWS Service Fee": applied_aws_revenue,
            "Total Revenue"  : current_total_rev,
            "OPEX Budget"    : current_opex,
            "Usage Rate (c/kWh)"  : village_u_rate,
            "Daily Supply ($/day)": village_d_daily,
        }
        numbers_sim = {
            "Total Cost"     : village_total_cost,
            "Seene Costs"    : seene_costs,
            "Usage Revenue"  : sim_usage_rev,
            "Supply Revenue" : sim_supply_rev,
            "AWS Service Fee": sim_aws_revenue,
            "Total Revenue"  : sim_total_rev,
            "OPEX Budget"    : sim_opex,
            "Usage Rate (c/kWh)"  : usage_rate_sim,
            "Daily Supply ($/day)": daily_sim,
        }
        explanations = {
            "Total Cost" : "Input from invoices",
            "Seene Costs": "Fixed platform cost",
            "Usage Revenue"  : "Total Usage × Usage Rate",
            "Supply Revenue" : "NMI × Daily Supply × 365",
            "AWS Service Fee": "Fixed annual amount (can be toggled on/off)",
            "Total Revenue"  : "Usage + Supply + AWS",
            "OPEX Budget"    : "Total Cost + Seene − (Usage + Supply + AWS)",
            "Usage Rate (c/kWh)"  : "Current tariff",
            "Daily Supply ($/day)": "Current tariff",
        }
    else:
        numbers_current = {
            "Total Cost"     : village_total_cost,
            "Seene Costs"    : seene_costs,
            "Usage Revenue"  : current_usage_rev,
            "Supply Revenue" : current_supply_rev,
            "Total Revenue"  : current_total_rev,
            "OPEX Budget"    : current_opex,
            "Usage Rate (c/kWh)"  : village_u_rate,
            "Daily Supply ($/day)": village_d_daily,
        }
        numbers_sim = {
            "Total Cost"     : village_total_cost,
            "Seene Costs"    : seene_costs,
            "Usage Revenue"  : sim_usage_rev,
            "Supply Revenue" : sim_supply_rev,
            "Total Revenue"  : sim_total_rev,
            "OPEX Budget"    : sim_opex,
            "Usage Rate (c/kWh)"  : usage_rate_sim,
            "Daily Supply ($/day)": daily_sim,
        }
        explanations = {
            "Total Cost" : "Input from invoices",
            "Seene Costs": "Fixed platform cost",
            "Usage Revenue"  : "Total Usage × Usage Rate",
            "Supply Revenue" : "NMI × Daily Supply × 365",
            "Total Revenue"  : "Usage + Supply",
            "OPEX Budget"    : "Total Cost + Seene − (Usage + Supply)",
            "Usage Rate (c/kWh)"  : "Current tariff",
            "Daily Supply ($/day)": "Current tariff",
        }

    def fmt(v, row):
        if "Rate" in row or "Supply ($/day)" in row:
            return f"{v:.4f}" if "Supply" in row else f"{v:.2f}"
        return money(v)

    comparison_df = pd.DataFrame({
        "Current"  : [fmt(numbers_current[k], k) for k in numbers_current],
        "Simulated": [fmt(numbers_sim[k], k)     for k in numbers_current],
        "Formula / Note": [explanations[k] for k in numbers_current],
    }, index=numbers_current.keys())

    def highlight_rows(row):
        idx = row.name
        if idx in {"Total Cost", "Seene Costs"}:
            return ['background-color:#f8d7da;color:#721c24']*3   # red
        if idx in {"Usage Revenue", "Supply Revenue", "AWS Service Fee", "Total Revenue"}:
            return ['background-color:#d4edda;color:#155724']*3   # green
        if idx == "OPEX Budget":
            return ['background-color:#ffe8cc;color:#7f3b00']*3   # orange
        return ['']*3

    st.table(comparison_df.style.apply(highlight_rows, axis=1))
# =================================================================
# TAB 3 — WHOLESALE PRICING (unchanged from your version)
# =================================================================
with tab_wholesale:
    st.markdown("## Australian Residential Electricity Price Map")

    @st.cache_data(show_spinner=False)
    def get_wholesale_df() -> pd.DataFrame:
        raw = (client.table("wholesale_price_nem")
                      .select("state,year,quarter,average_price")
                      .execute()
                      .data)
        df = pd.DataFrame(raw)
        df.columns = [c.strip().lower() for c in df.columns]
        for col in {"state","year","quarter","average_price"} - set(df.columns):
            df[col] = pd.NA
        df["period"] = (
            pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int).astype(str)
            + "-" + df["quarter"].str.upper().str.strip()
        )
        return df

    w_df = get_wholesale_df()
    w_df = w_df[w_df["year"].astype(int) >= 2021]   # filter

    periods = sorted(w_df["period"].unique(), key=lambda p: (int(p[:4]), p[5:]))
    pos_map = {p:i for i,p in enumerate(periods)}
    w_df["pos"] = w_df["period"].map(pos_map)

    w_df = (w_df.sort_values(["state","year","quarter"])
                  .groupby("state")
                  .apply(lambda d: d.assign(smoothed=d["average_price"].rolling(4, min_periods=1).mean()))
                  .reset_index(drop=True))

    all_states = sorted(w_df["state"].dropna().unique())
    years      = sorted({p[:4] for p in periods})
    ticks      = [pos_map[f"{y}-Q1"] for y in years if f"{y}-Q1" in pos_map]

    sel_states_smoothed = st.multiselect(
        "Show states:", all_states, default=all_states, key="nem_smoothed_states"
    )

    fig3, ax3 = plt.subplots(figsize=(8, 3.5))
    for state, grp in w_df.groupby("state"):
        if state in sel_states_smoothed:
            ax3.plot(grp["pos"], (grp["smoothed"] / 10) + 23,
                     marker="o", linewidth=2, label=state)

    ax3.set_xticks(ticks)
    ax3.set_xticklabels(years, rotation=90)
    ax3.set_xlabel("Year")
    ax3.set_ylabel("Average Price (c/kWh)")
    ax3.set_title("Rolling Average by State")
    ax3.grid(axis="y", alpha=0.3)
    ax3.legend(title="State", bbox_to_anchor=(1.02, 0.5), loc="center left")
    st.pyplot(fig3)

# =================================================================
# TAB 4 — CONSULTANT NOTES
# =================================================================
with tab_notes:
    st.markdown("## Consultant Comments & Observations")
    st.markdown(f"""

- **Energy Price Trends**: Four-quarter rolling average shows stabilisation post-2023 and with a forward look for further increases in prices over the coming years.
- **OPEX Budget** Your OPEX budget is covering the remainder of the Gate meter bill after the Revenue from the AWS Service Fee, Usage and Supply charges.
- **AWS Contribution**: AWS Service Fee is a fixed amount per residence, it will increase in proportion to the increase in the Usage and Supply charges. You can now toggle this fee on/off using the checkbox in the sidebar.
- **Seene Costs**: Seene costs are fixed and will not change with the increase in the Usage and Supply charges.
- **Competitor Positioning**: Village rates are very competitive.
    - *Usage Rate*: The current usage rate is 22.11c/kWh. 
    - *Supply Rate*: The current supply rate is $1.073/Day. 
- **Suggested Rates**
    - *Usage Rate*: The proposed usage rate is 27.00c/kWh. 
    - *Supply Rate*: The proposed supply rate is $1.1/Day""")
