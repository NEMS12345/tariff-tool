<<<<<<< HEAD
=======

>>>>>>> c438aeaec3baf340febbf09fd9c7f63a3c463f17
import streamlit as st
from supabase import create_client, Client

# MUST BE FIRST
st.set_page_config(page_title="Tariff Tool", layout="wide")

# --------------------------------------
# SUPABASE CONFIG
# --------------------------------------
SUPABASE_URL = "https://nivriefipgzsqexdnhaa.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5pdnJpZWZpcGd6c3FleGRuaGFhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY4NTIyMDEsImV4cCI6MjA2MjQyODIwMX0.trAUIqGoZ2fOOu8C1CUlhnvNDFpRt7CIH4SxPegP1Ag"

@st.cache_resource
def load_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = load_supabase_client()

# --------------------------------------
# HELPER
# --------------------------------------
def safe_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0

# --------------------------------------
# SELECT VILLAGE & FETCH DATA
# --------------------------------------
VILLAGE_NAMES = {
    "Classic Res": "Classic Residences Brighton",
}

village_list_response = supabase.table("village_inputs").select("village_name").execute()

village_options = [
    (VILLAGE_NAMES.get(row["village_name"].strip(), row["village_name"].strip()), row["village_name"].strip())
    for row in village_list_response.data if row.get("village_name")
]

if not village_options:
    st.error("No village options found.")
    st.stop()

village_display_names = sorted([label for label, _ in village_options])
selected_display_name = st.sidebar.selectbox("Select Village", village_display_names)
village_name = next((original for label, original in village_options if label == selected_display_name), None)

if not village_name:
    st.error("Selected village not found. Please check the data.")
    st.stop()

response = supabase.table("village_inputs").select("*").eq("village_name", village_name).execute()
if not response.data:
    st.error(f"No data found for '{village_name}'")
    st.stop()
row = response.data[0]

# --------------------------------------
# INPUT MODE & COMPETITOR OFFER FETCH
# --------------------------------------
input_mode = st.sidebar.radio(
    "Tariff Input Mode",
    options=["Manual Input", "Competitor Offer"],
    index=0,
    help="Toggle between your own rates or competitor pricing"
)

competitor_data = (
    supabase.table("competitor_offers")
    .select("*")
    .eq("village_name", village_name)
    .execute()
).data
competitor_offer = competitor_data[0] if competitor_data else None

if input_mode == "Competitor Offer" and competitor_offer:
    retailer_map = {
        "agl": ["agl_usage_rate", "agl_daily_charge"],
        "ea": ["ea_usage_rate", "ea_daily_charge"],
        "origin": ["origin_usage_rate", "origin_daily_charge"],
        "alinta": ["alinta_usage_rate", "alinta_daily_charge"],
        "momentum": ["momentum_usage_rate", "momentum_daily_charge"],
        "actewagl": ["actewagl_usage_rate", "actewagl_daily_charge"]
    }
    available_retailers = [
        r for r, keys in retailer_map.items()
        if competitor_offer.get(keys[0]) is not None and competitor_offer.get(keys[1]) is not None
    ]
    if available_retailers:
        retailer_labels = {
            "agl": "AGL",
            "ea": "Energy Australia",
            "origin": "Origin",
            "alinta": "Alinta",
            "momentum": "Momentum",
            "actewagl": "ActewAGL"
        }
        retailer_display = [retailer_labels[r] for r in available_retailers]
        selected_label = st.sidebar.selectbox("Select Retailer", retailer_display)
        retailer = [key for key, value in retailer_labels.items() if value == selected_label][0]
    else:
        st.warning("No complete retailer offers available for this village.")
        input_mode = "Manual Input"

# --------------------------------------
# PULL VALUES FROM SUPABASE
# --------------------------------------
TOTAL_USAGE_GATE = safe_float(row.get("total_usage_kwh"))
<<<<<<< HEAD
RESI_USAGE_DOLLARS = safe_float(row.get("child_billed_kwh"))
COMMON_USAGE_DOLLARS = safe_float(row.get("total_usage_common"))
=======
RESI_USAGE_KWH = safe_float(row.get("child_billed_kwh"))
METERED_COMMON_USAGE_KWH = safe_float(row.get("total_usage_common"))
>>>>>>> c438aeaec3baf340febbf09fd9c7f63a3c463f17
NMIS_RES = safe_float(row.get("nmis_res"))
NMIS_COMMON = safe_float(row.get("nmis_common"))
DAYS_IN_YEAR = 365
TOTAL_SITE_COST = safe_float(row.get("total_cost"))

<<<<<<< HEAD
=======
ACTUAL_RESI_REVENUE_CY24 = safe_float(row.get("total_usage_res")) + safe_float(row.get("total_supply_res"))
ACTUAL_COMMON_REVENUE_CY24 = safe_float(row.get("total_usage_common")) + safe_float(row.get("total_supply_common"))

>>>>>>> c438aeaec3baf340febbf09fd9c7f63a3c463f17
PROPOSED_USAGE = safe_float(row.get("proposed_usage_c_per_kwh", 20.0))
PROPOSED_DAILY = safe_float(row.get("proposed_daily_c", 100.0)) / 100.0

# --------------------------------------
# SIDEBAR INPUTS
# --------------------------------------
if input_mode == "Manual Input":
    usage_rate = st.sidebar.number_input("Usage Rate (c/kWh)", min_value=0.0, max_value=100.0, value=PROPOSED_USAGE, step=0.01, format="%.2f")
    daily_supply = st.sidebar.number_input("Daily Supply Charge ($/day)", min_value=0.0, max_value=5.0, value=PROPOSED_DAILY, step=0.0001, format="%.4f")
elif competitor_offer:
    usage_key = f"{retailer}_usage_rate"
    supply_key = f"{retailer}_daily_charge"
    usage_rate = safe_float(competitor_offer.get(usage_key, PROPOSED_USAGE))
    daily_supply = safe_float(competitor_offer.get(supply_key, PROPOSED_DAILY * 100)) / 100
    st.sidebar.metric("🔌 Usage Rate (c/kWh)", f"{usage_rate:.2f}")
    st.sidebar.metric("📆 Daily Supply ($/day)", f"${daily_supply:.4f}")
else:
<<<<<<< HEAD
=======
    st.warning("No competitor offer found for this village. Defaulting to manual input.")
>>>>>>> c438aeaec3baf340febbf09fd9c7f63a3c463f17
    usage_rate = PROPOSED_USAGE
    daily_supply = PROPOSED_DAILY

# --------------------------------------
<<<<<<< HEAD
# CALCULATIONS
# --------------------------------------
resi_usage_rev = RESI_USAGE_DOLLARS
resi_supply_rev = daily_supply * NMIS_RES * DAYS_IN_YEAR

common_usage_rev = COMMON_USAGE_DOLLARS
common_supply_rev = daily_supply * NMIS_COMMON * DAYS_IN_YEAR
=======
# CALCULATION FUNCTION
# --------------------------------------
def calculate_tariff_impact(usage_kwh, nmis, usage_rate_c_per_kwh, daily_supply_dollars):
    usage_kwh = safe_float(usage_kwh)
    nmis = safe_float(nmis)
    usage_rate_dollars = usage_rate_c_per_kwh / 100.0
    usage_revenue = usage_rate_dollars * usage_kwh
    supply_revenue = daily_supply_dollars * nmis * DAYS_IN_YEAR
    projected_revenue = usage_revenue + supply_revenue
    return usage_revenue, supply_revenue, projected_revenue

# --------------------------------------
# CALCULATIONS
# --------------------------------------
unmetered_usage_kwh = max(0.0, safe_float(TOTAL_USAGE_GATE) - (safe_float(RESI_USAGE_KWH) + safe_float(METERED_COMMON_USAGE_KWH)))

resi_usage_rev, resi_supply_rev, _ = calculate_tariff_impact(RESI_USAGE_KWH, NMIS_RES, usage_rate, daily_supply)
common_usage_rev, common_supply_rev, _ = calculate_tariff_impact(METERED_COMMON_USAGE_KWH, NMIS_COMMON, usage_rate, daily_supply)
>>>>>>> c438aeaec3baf340febbf09fd9c7f63a3c463f17

total_res = (resi_usage_rev + resi_supply_rev) * 1.10
total_common = (common_usage_rev + common_supply_rev) * 1.10

<<<<<<< HEAD
unmetered_usage_kwh = max(0.0, safe_float(TOTAL_USAGE_GATE) - (safe_float(RESI_USAGE_DOLLARS) + safe_float(COMMON_USAGE_DOLLARS)))
unbilled_cost = TOTAL_SITE_COST - (total_res + total_common)
unbilled_cost_per_res_nmi_annual = unbilled_cost / NMIS_RES if NMIS_RES else 0
unbilled_cost_per_res_nmi_daily = unbilled_cost_per_res_nmi_annual / DAYS_IN_YEAR
unrecovered_cost = TOTAL_SITE_COST - (total_res + total_common)
=======
unbilled_cost = TOTAL_SITE_COST - (total_res + total_common)
unbilled_cost_per_res_nmi_annual = unbilled_cost / NMIS_RES if NMIS_RES else 0
unbilled_cost_per_res_nmi_daily = unbilled_cost_per_res_nmi_annual / DAYS_IN_YEAR

combined_billed_revenue = total_res + total_common
unrecovered_cost = TOTAL_SITE_COST - combined_billed_revenue
>>>>>>> c438aeaec3baf340febbf09fd9c7f63a3c463f17

# --------------------------------------
# DISPLAY
# --------------------------------------
st.markdown(""" 
    <style>
    h1 { font-size: 1.5rem !important; margin-bottom: 0.5rem !important; }
    div[data-testid="metric-container"] > div > p { font-size: 0.9rem !important; }
    div[data-testid="metric-container"] > div > div { font-size: 1rem !important; }
    .css-18e3th9 { padding: 0.5rem 1rem !important; }
    </style>
""", unsafe_allow_html=True)

st.title(f"\U0001F4CA {village_name} — Tariff Assessment")

res_col, common_col = st.columns(2)
with res_col:
    st.subheader("\U0001F3E0 Residential Revenue")
    st.metric("\U0001F50C Usage Revenue", f"${resi_usage_rev:,.2f}")
    st.metric("\U0001F4C6 Daily Supply Revenue", f"${resi_supply_rev:,.2f}")
    st.metric("\U0001F4B0 Total Residential Revenue (incl. GST)", f"${total_res:,.2f}")

with common_col:
    st.subheader("\U0001F3E2 Common Area Revenue")
    st.metric("\U0001F50C Usage Revenue", f"${common_usage_rev:,.2f}")
    st.metric("\U0001F4C6 Daily Supply Revenue", f"${common_supply_rev:,.2f}")
    st.metric("\U0001F4B0 Total Metered Common Revenue (incl. GST)", f"${total_common:,.2f}")

st.markdown("---")
unbilled_col, allocation_col = st.columns(2)
with unbilled_col:
    st.subheader("⚠️ Unmetered Common Area Usage")
    st.metric("⚡ Unmetered Usage (kWh)", f"{unmetered_usage_kwh:,.0f} kWh")
    st.metric("\U0001F4B0 Unbilled Usage Cost (Gap to Recover)", f"${unbilled_cost:,.2f}")

with allocation_col:
    st.subheader("\U0001F4CA Unbilled Usage Cost Allocation")
    st.metric("\U0001F3E2 Annual Cost per Residential NMI", f"${unbilled_cost_per_res_nmi_annual:,.2f}")
    st.metric("\U0001F4C5 Daily Cost per Residential NMI", f"${unbilled_cost_per_res_nmi_daily:,.4f}")

st.markdown("---")
st.subheader("⚠️ Unrecovered Gate Meter Cost")
st.metric(label="\U0001F4B0 Cost Not Recovered via Billing", value=f"${unrecovered_cost:,.2f}")
