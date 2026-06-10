"""
A/B Testing + Decision Analysis Dashboard – Home
Run with:  streamlit run app.py
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.state import (
    PAGE_KWARGS, get_config, get_df, set_df, data_source,
    run_stats, run_bayes, sidebar_data_status,
    DEMO_SCENARIOS, simulate_scenario,
)
from utils.data_loader import load_data, load_uploaded_data, get_sample_sizes, get_date_range
from utils.formatting import fmt_pct, fmt_pvalue

st.set_page_config(page_title="A/B Test Decision Dashboard", page_icon="🧪", **PAGE_KWARGS)

config = get_config()
df = get_df()

# header

st.markdown('<p class="kicker">EXPERIMENT REPORT &middot; A/B TESTING &middot; DECISION ENGINE</p>', unsafe_allow_html=True)
st.title("A/B Testing + Decision Analysis Dashboard")
st.markdown(
    "Most A/B testing tools stop at p-values. This one translates statistical results "
    "into **business decisions** – revenue impact, risk-adjusted recommendations, "
    "and Bayesian probability of winning."
)

# data source

st.subheader("Data source")

tab_demo, tab_upload = st.tabs(["Demo experiment", "Upload your own CSV"])

with tab_demo:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"**{config['experiment_name']}**")
        st.markdown(f"*Hypothesis:* {config.get('hypothesis', '—')}")
        st.markdown(
            f"- {config.get('control_label', 'Control')} vs {config.get('treatment_label', 'Treatment')}\n"
            f"- {config['sample_size_per_group']:,} users per group\n"
            f"- Revenue per conversion: ${config['revenue_per_conversion']:,.2f}"
        )
    with col2:
        st.markdown(
            "**Demo scenario**",
            help="Each button regenerates the synthetic data with a different TRUE "
                 "treatment effect, so you can verify the decision engine reaches "
                 "the right call in each world (SHIP / CONTINUE TESTING / DO NOT SHIP).",
        )
        for scenario, rate in DEMO_SCENARIOS.items():
            if st.button(scenario, use_container_width=True, key=f"scenario_{rate}"):
                set_df(simulate_scenario(rate), f"Demo: {scenario}")
                st.rerun()

with tab_upload:
    st.markdown(
        "CSV must contain columns: `user_id`, `group` (control/treatment), "
        "`converted` (0/1), `revenue`, `timestamp`. Optional: `device`, `session_length_sec`."
    )
    uploaded = st.file_uploader("Upload experiment CSV", type=["csv"], label_visibility="collapsed")
    if uploaded is not None:
        try:
            new_df = load_uploaded_data(uploaded)
            set_df(new_df, f"Uploaded: {uploaded.name}")
            st.success(f"Loaded {len(new_df):,} rows from {uploaded.name}")
        except ValueError as e:
            st.error(str(e))

df = get_df()  # refresh after any change

# headline metrics

st.subheader("At a glance")

conv = run_stats(
    df,
    alpha=st.session_state.get("alpha", 0.05),
    mde_relative_pct=st.session_state.get("mde", 10.0),
    target_power=st.session_state.get("target_power", 0.80),
)["conversion"]
bayes_result = run_bayes(
    df,
    prior_alpha=st.session_state.get("prior_alpha", 1.0),
    prior_beta=st.session_state.get("prior_beta", 1.0),
)["result"]
sizes = get_sample_sizes(df)

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Control rate", fmt_pct(conv.control_rate))
m2.metric(
    "Treatment rate",
    fmt_pct(conv.treatment_rate),
    delta=fmt_pct(conv.absolute_lift, sign=True),
)
m3.metric("Relative lift", f"{conv.relative_lift_pct:+.1f}%")
m4.metric("P-value", fmt_pvalue(conv.p_value).replace("p = ", "").replace("p < ", "<"))
m5.metric("P(treatment best)", fmt_pct(bayes_result.prob_treatment_better, decimals=1))

p_best = bayes_result.prob_treatment_better
st.markdown(
    f"""
<div style="margin:10px 0 2px;font-size:0.78rem;letter-spacing:0.06em;color:#8E8478;">PROBABILITY SPLIT &mdash; WHO WINS?</div>
<div style="height:12px;border-radius:6px;overflow:hidden;display:flex;border:1px solid #E3CDBA;">
  <div style="width:{(1 - p_best) * 100:.1f}%;background:#0F5499;"></div>
  <div style="width:{p_best * 100:.1f}%;background:#990F3D;"></div>
</div>
<div style="display:flex;justify-content:space-between;font-family:'IBM Plex Mono',monospace;font-size:0.78rem;margin:4px 0 14px;">
  <span style="color:#0F5499;">A &middot; Control {(1 - p_best) * 100:.1f}%</span>
  <span style="color:#990F3D;">Treatment &middot; B {p_best * 100:.1f}%</span>
</div>
""",
    unsafe_allow_html=True,
)

if conv.significant and bayes_result.prob_treatment_better >= 0.95:
    st.success("Both frameworks agree: the treatment effect looks real. See the **Decision Centre** for the launch recommendation.")
elif conv.significant or bayes_result.prob_treatment_better >= 0.80:
    st.warning("Evidence is promising but mixed – dig into the analysis pages before deciding.")
else:
    st.info("No clear winner yet. Check the power analysis – the test may be underpowered.")

# data preview

with st.expander("Preview data"):
    dates = get_date_range(df)
    cols = st.columns(3)
    cols[0].markdown(f"**Rows:** {sizes['total']:,}")
    cols[1].markdown(f"**Control / Treatment:** {sizes['control']:,} / {sizes['treatment']:,}")
    if dates:
        cols[2].markdown(f"**Period:** {dates['start']:%d %b %Y} → {dates['end']:%d %b %Y} ({dates['days']} days)")
    st.dataframe(df.head(50), use_container_width=True)

# page guide

st.subheader("Pages")
st.markdown(
    """
| Page | What it answers |
|---|---|
| **1 · Experiment Overview** | Is the data healthy? Sample sizes, SRM check, segments, trends |
| **2 · Frequentist Analysis** | Is the lift statistically significant? z-test, CIs, power |
| **3 · Bayesian Analysis** | What's the probability treatment is actually better? |
| **4 · Decision Centre** | Should we ship? Revenue impact, risk/reward, scenarios |
| **5 · Report Summary** | One-page exportable summary of everything |
"""
)

sidebar_data_status()