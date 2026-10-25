import streamlit as st

st.set_page_config(
    page_title="Business Case | ClearLedger",
    page_icon="↔",
    layout="wide",
)

st.title("Benefits model")
st.caption(
    "Editable planning assumptions for a potential reconciliation pilot. "
    "These are scenarios, not measured savings or an approved business case."
)
st.warning(
    "The app has no measured operating baseline. Validate each input with "
    "Finance and the process owner before using these estimates in a decision."
)

st.subheader("Scenario assumptions")
first, second = st.columns(2)
with first:
    transactions = st.slider(
        "Transactions reconciled per month",
        min_value=100,
        max_value=10_000,
        value=1_000,
        step=100,
    )
    manual_minutes = st.slider(
        "Manual handling time per transaction (minutes)",
        min_value=2,
        max_value=30,
        value=8,
    )
    time_reduction = st.slider(
        "Potential handling-time reduction",
        min_value=0,
        max_value=80,
        value=40,
        format="%d%%",
    )
with second:
    adoption = st.slider(
        "Assumed adoption of the workflow",
        min_value=0,
        max_value=100,
        value=70,
        format="%d%%",
    )
    hourly_cost = st.number_input(
        "Loaded staff cost per hour (TZS)",
        min_value=0,
        max_value=500_000,
        value=15_000,
        step=1_000,
    )
    implementation_cost = st.number_input(
        "One-time implementation estimate (TZS)",
        min_value=0,
        max_value=5_000_000_000,
        value=0,
        step=100_000,
    )
    monthly_operating_cost = st.number_input(
        "Monthly operating cost estimate (TZS)",
        min_value=0,
        max_value=500_000_000,
        value=0,
        step=50_000,
    )

hours_released_monthly = (
    transactions * manual_minutes * (time_reduction / 100) * (adoption / 100) / 60
)
capacity_value_monthly = hours_released_monthly * hourly_cost
annual_capacity_value = capacity_value_monthly * 12
annual_operating_cost = monthly_operating_cost * 12
annual_net_capacity_value = annual_capacity_value - annual_operating_cost

st.subheader("Indicative scenario output")
kpis = st.columns(4)
kpis[0].metric("Capacity released / month", f"{hours_released_monthly:,.1f} hours")
kpis[1].metric("Capacity value / month", f"TZS {capacity_value_monthly:,.0f}")
kpis[2].metric("Annual capacity value", f"TZS {annual_capacity_value:,.0f}")
kpis[3].metric("Annual operating estimate", f"TZS {annual_operating_cost:,.0f}")

if implementation_cost > 0 and annual_net_capacity_value > 0:
    payback_months = implementation_cost / (annual_net_capacity_value / 12)
    st.metric("Indicative payback", f"{payback_months:,.1f} months")
else:
    st.info(
        "Enter non-zero implementation and operating cost assumptions to see a "
        "payback scenario. The current values are not verified project costs."
    )

st.markdown(
    """
    ### How to interpret this

    **Capacity value is not automatically a cash saving.** It estimates the
    notional value of staff time that could be released under the selected
    assumptions. A realised financial benefit requires measured outcomes and
    evidence that the capacity was redeployed or costs were actually reduced.

    **Formula:** monthly capacity hours = monthly volume × manual minutes ×
    assumed time reduction × adoption ÷ 60. Monthly capacity value = hours ×
    loaded hourly cost. Annual estimates multiply the monthly scenario by 12.

    Start with a measured manual baseline, compare a representative pilot, and
    record data source, owner, measurement period, and assumptions. These
    forecasts are not evidence of benefits at any named organization.
    """
)
