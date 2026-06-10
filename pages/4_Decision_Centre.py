"""Page 4 – Decision Centre: revenue impact, risk/reward, scenarios, final call."""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.state import (
    PAGE_KWARGS, get_config, get_df, run_stats, run_bayes, run_decision,
    sidebar_data_status,
)
from utils.formatting import fmt_pct, fmt_currency, fmt_currency_signed
from utils.plotting import plot_revenue_impact, plot_scenario_analysis

st.set_page_config(page_title="Decision Centre", page_icon="⚖️", **PAGE_KWARGS)

config = get_config()
df = get_df()

st.title("Decision Centre")
st.markdown("Where statistics become a business decision.")

# business inputs

with st.sidebar:
    st.header("Business assumptions")
    if "rev_w_dc" not in st.session_state:
        st.session_state["rev_w_dc"] = float(st.session_state.get("rev_per_conv", config["revenue_per_conversion"]))
    if "vis_w_dc" not in st.session_state:
        st.session_state["vis_w_dc"] = int(st.session_state.get("daily_visitors", 5_000))
    if "split_w_dc" not in st.session_state:
        st.session_state["split_w_dc"] = float(st.session_state.get("traffic_split", 0.5))
    rev_per_conv = st.number_input(
        "Revenue per conversion ($)", min_value=0.0, step=5.0, key="rev_w_dc")
    daily_visitors = st.number_input(
        "Daily site visitors", min_value=100, step=500, key="vis_w_dc",
        help="Total daily traffic that would see the shipped variant.")
    traffic_split = st.slider(
        "Traffic share affected", 0.1, 1.0, step=0.05, key="split_w_dc",
        help="During the test only half of traffic sees treatment; after full rollout this is 100%.")
    st.session_state["rev_per_conv"] = rev_per_conv
    st.session_state["daily_visitors"] = daily_visitors
    st.session_state["traffic_split"] = traffic_split

alpha = st.session_state.get("alpha", 0.05)
prior_a = st.session_state.get("prior_alpha", 1.0)
prior_b = st.session_state.get("prior_beta", 1.0)
st.caption(
    f"Using your analysis settings: α = {alpha}, prior Beta({prior_a:g}, {prior_b:g}) "
    "– change these on the Frequentist / Bayesian pages."
)

stats_results = run_stats(
    df, alpha=alpha,
    mde_relative_pct=st.session_state.get("mde", 10.0),
    target_power=st.session_state.get("target_power", 0.80),
)
bayes_results = run_bayes(df, prior_alpha=prior_a, prior_beta=prior_b)
decision = run_decision(
    stats_results["conversion"],
    bayes_results["result"],
    revenue_per_conversion=rev_per_conv,
    daily_visitors=int(daily_visitors),
    traffic_split=traffic_split,
)

dec = decision["decision"]
rev = decision["revenue_impact"]
rr = decision["risk_reward"]

# recommendation banner

banner = {
    "SHIP": st.success,
    "DO NOT SHIP": st.error,
    "CONTINUE TESTING": st.warning,
}.get(dec.recommendation, st.info)

banner(
    f"## Recommendation: **{dec.recommendation}**\n"
    f"Confidence: **{dec.confidence}** · Risk: **{dec.risk_rating}**"
)

with st.expander("Rationale", expanded=True):
    for point in dec.rationale:
        # escape $ so markdown doesn't render dollar amounts as LaTeX math
        st.markdown(f"- {point}".replace("$", "\\$"))

# revenue impact

st.subheader("Revenue impact")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Daily conversion lift", f"{rev.daily_conversion_lift:+.1f} / day")
m2.metric("Daily revenue lift", fmt_currency_signed(rev.daily_revenue_lift))
m3.metric("Annual revenue lift", fmt_currency_signed(rev.annual_revenue_lift))
m4.metric(
    "Annual range (95% CI)",
    f"{fmt_currency(rev.annual_revenue_lift_low)} – {fmt_currency(rev.annual_revenue_lift_high)}",
)

st.plotly_chart(plot_revenue_impact(rev), use_container_width=True)
st.caption(
    f"Assumes {int(daily_visitors):,} daily visitors, {traffic_split:.0%} affected, "
    f"${rev_per_conv:,.2f} per conversion. Annualising a 2-week test is a simplification – "
    "seasonality and novelty effects can erode the lift."
)

# risk / reward

st.subheader("Risk vs reward")

r1, r2, r3, r4 = st.columns(4)
r1.metric("Upside (if treatment wins)", f"{fmt_currency(rr.upside_daily_revenue)}/day")
r2.metric("Downside (if treatment loses)", f"-{fmt_currency(rr.downside_daily_revenue)}/day")
r3.metric("EV of shipping", f"{fmt_currency_signed(rr.ev_ship_treatment)}/day")
r4.metric("P(treatment better)", fmt_pct(rr.prob_treatment_better, decimals=1))

st.markdown(
    f"Expected value weights the upside by P(better) = {fmt_pct(rr.prob_treatment_better, decimals=1)} "
    f"and the downside by P(worse) = {fmt_pct(1 - rr.prob_treatment_better, decimals=1)}. "
    f"Shipping has positive EV when the probability-weighted gain exceeds the probability-weighted loss."
)

# scenarios

st.subheader("Scenario analysis")
st.markdown(
    "Stress-testing the decision: what does the annual impact look like if the true "
    "effect sits at the bottom of the CI, the top, or doesn't exist at all?"
)

st.plotly_chart(plot_scenario_analysis(decision["scenarios"]), use_container_width=True)
st.dataframe(decision["scenarios"], use_container_width=True, hide_index=True)

sidebar_data_status()