import requests
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

DEFAULT_API = "http://127.0.0.1:8000"


def api_get(endpoint):
    r = requests.get(f"{DEFAULT_API}{endpoint}", timeout=10)
    r.raise_for_status()
    return r.json()


def api_post(endpoint):
    r = requests.post(f"{DEFAULT_API}{endpoint}", timeout=10)
    r.raise_for_status()
    return r.json()


def extract_nowcast(data):

    if "nowcast_value" in data:
        return float(data["nowcast_value"])

    nowcast = data.get("nowcast", 0)

    if isinstance(nowcast, dict):
        return float(nowcast.get("real_inflation_estimate", 0))

    return float(nowcast)


def regime_color(regime):

    if regime == "HIGH INFLATION REGIME":
        return "red"

    if regime == "MODERATE INFLATION":
        return "orange"

    return "green"


def regime_score(regime):

    if regime == "LOW INFLATION":
        return 33

    if regime == "MODERATE INFLATION":
        return 66

    if regime == "HIGH INFLATION REGIME":
        return 100

    return 0


st.set_page_config(
    page_title="Inflation Radar",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Inflation Radar – Macro Dashboard")

# ---------------------------------------------------
# Sidebar
# ---------------------------------------------------

with st.sidebar:

    st.header("System")

    if st.button("Create Snapshot"):
        res = api_post("/snapshot")
        st.success(f"Snapshot saved {res['snapshot']['date']}")

    st.write("")

    if st.checkbox("Show raw JSON"):
        show_json = True
    else:
        show_json = False


# ---------------------------------------------------
# Load API data
# ---------------------------------------------------

inflation = api_get("/inflation")
regime_data = api_get("/regime")
signals = api_get("/signals")
history = api_get("/history")

nowcast = extract_nowcast(inflation)

regime = regime_data["regime"]

gold_signal = signals.get("gold_signal")

history_df = pd.DataFrame(history["history"])

if not history_df.empty:
    history_df["date"] = pd.to_datetime(history_df["date"])


# ---------------------------------------------------
# Tabs Layout
# ---------------------------------------------------

tabs = st.tabs([
    "Overview",
    "History",
    "Allocation",
    "Signals",
    "Research"
])

# ===================================================
# OVERVIEW
# ===================================================

with tabs[0]:

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Real Inflation", f"{inflation['real_inflation']:.2f}%")

    with c2:
        st.metric("Nowcast", f"{nowcast:.2f}%")

    with c3:
        st.metric("Consumer Score", f"{inflation['consumer_score']:.2f}")

    with c4:
        st.metric("Monetary Score", f"{inflation['monetary_score']:.2f}")

    st.divider()

    left, right = st.columns([2, 1])

    with left:

        df = pd.DataFrame({
            "Component": [
                "Consumer",
                "Asset",
                "Monetary",
                "Real Inflation",
                "Nowcast"
            ],

            "Value": [
                inflation["consumer_score"],
                inflation["asset_score"],
                inflation["monetary_score"],
                inflation["real_inflation"],
                nowcast
            ]
        })

        fig = px.bar(df, x="Component", y="Value",
                     title="Inflation Components")

        st.plotly_chart(fig, use_container_width=True)

    with right:

        gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=regime_score(regime),
            title={"text": regime},
            gauge={"axis": {"range": [0, 100]},
                   "bar": {"color": regime_color(regime)}}
        ))

        st.plotly_chart(gauge)

        st.metric("Gold Signal", gold_signal)

# ===================================================
# HISTORY
# ===================================================

with tabs[1]:

    st.subheader("Inflation Timeline")

    if history_df.empty:

        st.info("Create snapshots to build history.")

    else:

        fig = px.line(
            history_df,
            x="date",
            y=["real_inflation", "nowcast"],
            title="Real Inflation vs Nowcast"
        )

        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(history_df)

# ===================================================
# ALLOCATION
# ===================================================

with tabs[2]:

    st.subheader("Asset Allocation Engine")

    if regime == "HIGH INFLATION REGIME":

        weights = {
            "Gold": 30,
            "Commodities": 25,
            "Inflation Bonds": 20,
            "Equities": 15,
            "Nominal Bonds": 10
        }

    elif regime == "MODERATE INFLATION":

        weights = {
            "Gold": 20,
            "Commodities": 15,
            "Inflation Bonds": 20,
            "Equities": 30,
            "Nominal Bonds": 15
        }

    else:

        weights = {
            "Gold": 10,
            "Commodities": 5,
            "Inflation Bonds": 15,
            "Equities": 40,
            "Nominal Bonds": 30
        }

    alloc_df = pd.DataFrame({
        "Asset": list(weights.keys()),
        "Weight": list(weights.values())
    })

    fig = px.pie(alloc_df, names="Asset", values="Weight")

    st.plotly_chart(fig)

    st.dataframe(alloc_df)

# ===================================================
# SIGNALS
# ===================================================

with tabs[3]:

    st.subheader("Asset Signals")

    signal_df = pd.DataFrame(list(signals.items()),
                             columns=["Signal", "Value"])

    st.dataframe(signal_df)

# ===================================================
# RESEARCH
# ===================================================

with tabs[4]:

    st.subheader("Model Research")

    model_df = pd.DataFrame({

        "Metric": [
            "Consumer Score",
            "Asset Score",
            "Monetary Score",
            "Real Inflation",
            "Nowcast"
        ],

        "Value": [
            inflation["consumer_score"],
            inflation["asset_score"],
            inflation["monetary_score"],
            inflation["real_inflation"],
            nowcast
        ]
    })

    st.dataframe(model_df)

    st.caption("Future: regression calibration & ML models")


# ---------------------------------------------------
# Debug JSON
# ---------------------------------------------------

if show_json:

    st.divider()

    st.json(inflation)
    st.json(regime_data)
    st.json(signals)