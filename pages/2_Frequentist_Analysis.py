"""Page 2 – Frequentist Analysis: z-test, confidence intervals, power, chi-square."""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.stats_engine import StatsEngine
from utils.state import PAGE_KWARGS, get_df, sidebar_data_status
from utils.formatting import (
    fmt_pct, fmt_pvalue, fmt_stat, fmt_ci, significance_label,
)
from utils.plotting import plot_conversion_rates, plot_ci_overlap, plot_power_curve

st.set_page_config(page_title="Frequentist Analysis", page_icon="📐", **PAGE_KWARGS)

df = get_df()

st.title("Frequentist Analysis")

# controls 

with st.sidebar:
    st.header("Test settings")
    if "alpha_w" not in st.session_state:
        st.session_state["alpha_w"] = st.session_state.get("alpha", 0.05)
    alpha = st.select_slider(
        "Significance level (α)",
        options=[0.01, 0.05, 0.10],
        key="alpha_w",
        help="Probability of a false positive you're willing to accept. "
             "Applies everywhere: Decision Centre and the report use this too.",
    )
    st.session_state["alpha"] = alpha

engine = StatsEngine(df, alpha=alpha)
conv = engine.test_conversion_rate()
rev = engine.test_revenue_per_user()

# primary metric: conversion rate

st.subheader("Primary metric – conversion rate")
st.caption(conv.test_type)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Control", fmt_pct(conv.control_rate), help=f"95% CI {fmt_ci(*conv.control_ci)}")
m2.metric("Treatment", fmt_pct(conv.treatment_rate),
          delta=fmt_pct(conv.absolute_lift, sign=True),
          help=f"95% CI {fmt_ci(*conv.treatment_ci)}")
m3.metric("Z-statistic", fmt_stat(conv.z_statistic, decimals=3))
m4.metric("P-value", f"{conv.p_value:.4f}")

if conv.significant:
    st.success(f"**{significance_label(conv.p_value, alpha)}** at α = {alpha}. "
               f"The {conv.relative_lift_pct:+.1f}% relative lift is unlikely to be due to chance alone.")
else:
    st.warning(f"**{significance_label(conv.p_value, alpha)}** at α = {alpha}. "
               "The observed difference is consistent with random variation.")

c_left, c_right = st.columns(2)
with c_left:
    st.plotly_chart(plot_conversion_rates(conv), use_container_width=True)
with c_right:
    st.plotly_chart(plot_ci_overlap(conv), use_container_width=True)

st.caption(
    "Note: non-overlapping CIs imply significance, but overlapping CIs do **not** imply "
    "non-significance – the z-test on the difference is the authoritative result."
)

# secondary metric: revenue per user 

has_revenue = df["revenue"].abs().sum() > 0
if has_revenue:
    st.subheader("Secondary metric – revenue per user")
    st.caption(rev.test_type)
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Control mean", f"${rev.control_mean:.3f}")
    r2.metric("Treatment mean", f"${rev.treatment_mean:.3f}", delta=f"${rev.absolute_lift:+.3f}")
    r3.metric("T-statistic", fmt_stat(rev.t_statistic, decimals=3))
    r4.metric("Cohen's d", f"{rev.cohens_d:.4f}")

    st.markdown(
        f"{significance_label(rev.p_value, alpha)} – "
        f"relative lift {rev.relative_lift_pct:+.2f}%. "
        "Revenue per user includes all users (zeros for non-converters), so it captures "
        "both conversion *and* basket-size effects."
    )

# power analysis 

st.subheader("Power analysis")

p_col1, p_col2 = st.columns([1, 2])
with p_col1:
    if "mde_w" not in st.session_state:
        st.session_state["mde_w"] = st.session_state.get("mde", 10.0)
    mde = st.slider("Minimum detectable effect (relative %)", 2.0, 30.0,
                    step=1.0, key="mde_w",
                    help="The smallest relative lift you care about detecting. "
                         "Carries through to the report.")
    if "target_power_w" not in st.session_state:
        st.session_state["target_power_w"] = st.session_state.get("target_power", 0.80)
    target_power = st.slider("Target power", 0.70, 0.95, step=0.05, key="target_power_w")
    st.session_state["mde"] = mde
    st.session_state["target_power"] = target_power

power = engine.power_analysis(mde_relative_pct=mde, target_power=target_power)

with p_col2:
    pw1, pw2, pw3 = st.columns(3)
    pw1.metric("Required n / group", f"{power.required_n_per_group:,}")
    pw2.metric("Current n / group", f"{power.current_n_per_group:,}")
    pw3.metric("Achieved power", fmt_pct(power.achieved_power, decimals=1))

    if power.is_underpowered:
        st.warning(
            f"Underpowered for a {mde:.0f}% MDE – at the current sample size there's a "
            f"{(1 - power.achieved_power) * 100:.0f}% chance of missing a real effect of that size."
        )
    else:
        st.success(f"Adequately powered to detect a {mde:.0f}% relative lift.")

st.plotly_chart(plot_power_curve(engine), use_container_width=True)

# segment chi-square 

if "device" in df.columns:
    st.subheader("Segment check – device")
    chi = engine.chi_square_segment("device")
    st.markdown(
        f"{chi['test_type']}: χ² = {chi['chi2_statistic']:.3f}, "
        f"{fmt_pvalue(chi['p_value'])}, dof = {chi['degrees_of_freedom']} – "
        + ("conversion **does** vary by device; consider segmented analysis."
           if chi["significant"] else
           "no evidence conversion depends on device.")
    )
    with st.expander("Contingency table"):
        st.dataframe(chi["contingency_table"], use_container_width=True)

sidebar_data_status()