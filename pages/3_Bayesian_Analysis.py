"""Page 3 – Bayesian Analysis: priors, posteriors, P(best), expected loss."""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.state import PAGE_KWARGS, get_df, run_bayes, run_bayes_sample_size, sidebar_data_status
from utils.formatting import fmt_pct, fmt_ci
from utils.plotting import plot_posterior_distributions, plot_uplift_distribution

st.set_page_config(page_title="Bayesian Analysis", page_icon="🎲", **PAGE_KWARGS)

df = get_df()

st.title("Bayesian Analysis")
st.markdown(
    "Beta-Binomial conjugate model. Instead of asking *\"is this difference unlikely "
    "under the null?\"*, we ask the question stakeholders actually care about: "
    "**what is the probability the treatment is better, and how much do we lose if we're wrong?**"
)

# prior controls

with st.sidebar:
    st.header("Prior belief")
    _presets = ["Uniform Beta(1,1)", "Weakly informative", "Custom"]
    if "prior_preset_w" not in st.session_state:
        st.session_state["prior_preset_w"] = st.session_state.get("prior_preset", "Uniform Beta(1,1)")
    prior_preset = st.radio(
        "Prior",
        _presets,
        key="prior_preset_w",
        help="The prior encodes what you believed about the conversion rate before "
             "the experiment. Applies everywhere: Decision Centre and the report use it too.",
    )
    st.session_state["prior_preset"] = prior_preset
    if prior_preset == "Uniform Beta(1,1)":
        prior_alpha, prior_beta = 1.0, 1.0
    elif prior_preset == "Weakly informative":
        # centred near the observed control rate with ~100 pseudo-observations
        base = df[df["group"] == "control"]["converted"].mean()
        prior_alpha = round(base * 100, 1)
        prior_beta = round((1 - base) * 100, 1)
        st.caption(f"Beta({prior_alpha}, {prior_beta}) – centred on control rate, worth ~100 users of evidence.")
    else:
        if "prior_alpha_w" not in st.session_state:
            st.session_state["prior_alpha_w"] = float(st.session_state.get("prior_alpha", 1.0))
        if "prior_beta_w" not in st.session_state:
            st.session_state["prior_beta_w"] = float(st.session_state.get("prior_beta", 1.0))
        prior_alpha = st.number_input("Prior α", min_value=0.1, step=0.5, key="prior_alpha_w")
        prior_beta = st.number_input("Prior β", min_value=0.1, step=0.5, key="prior_beta_w")

st.session_state["prior_alpha"] = prior_alpha
st.session_state["prior_beta"] = prior_beta

results = run_bayes(df, prior_alpha=prior_alpha, prior_beta=prior_beta)
r = results["result"]

# headline metrics

m1, m2, m3, m4 = st.columns(4)
m1.metric("P(treatment > control)", fmt_pct(r.prob_treatment_better, decimals=1))
m2.metric("Expected uplift", f"{r.relative_uplift_pct:+.2f}%")
m3.metric("Expected loss if we ship", fmt_pct(r.expected_loss_treatment, decimals=4),
          help="Average conversion-rate regret if treatment is actually worse. Small = safe to ship.")
m4.metric("Expected loss if we keep control", fmt_pct(r.expected_loss_control, decimals=4),
          help="Average missed uplift if treatment is actually better.")

if r.prob_treatment_better >= 0.95:
    st.success(f"**{fmt_pct(r.prob_treatment_better, decimals=1)}** probability the treatment is better – exceeds the conventional 95% decision threshold.")
elif r.prob_treatment_better >= 0.80:
    st.warning(f"**{fmt_pct(r.prob_treatment_better, decimals=1)}** probability treatment is better – promising but below the 95% threshold.")
else:
    st.info("Posterior evidence does not clearly favour either variant.")

# posteriors + credible intervals

st.subheader("Posterior distributions")

c_left, c_right = st.columns([2, 1])
with c_left:
    st.plotly_chart(plot_posterior_distributions(results["curves"]), use_container_width=True)
with c_right:
    st.markdown("**Posterior summary**")
    st.markdown(
        f"""
| | Control | Treatment |
|---|---|---|
| Posterior | Beta({r.control_alpha:.0f}, {r.control_beta:.0f}) | Beta({r.treatment_alpha:.0f}, {r.treatment_beta:.0f}) |
| Mean | {fmt_pct(r.control_posterior_mean)} | {fmt_pct(r.treatment_posterior_mean)} |
| 95% credible interval | {fmt_ci(*r.control_credible_interval)} | {fmt_ci(*r.treatment_credible_interval)} |
"""
    )
    st.caption(
        "A 95% credible interval means: given the data and prior, there is a 95% "
        "probability the true rate lies in this range – the intuitive interpretation "
        "people *wrongly* give to frequentist confidence intervals."
    )

# uplift distribution

st.subheader("Uplift distribution")
st.markdown(
    "The full posterior over (treatment − control). The green share of mass **is** "
    "P(treatment better) – no p-value translation needed."
)
st.plotly_chart(plot_uplift_distribution(results["uplift_dist"]), use_container_width=True)

# bayesian sample size

with st.expander("Bayesian sample size estimate"):
    st.markdown(
        "Simulates how many users per group you'd need before P(treatment best) "
        "reaches your decision threshold. Tune the assumptions below – smaller "
        "effects or stricter thresholds need much larger samples."
    )
    ss_col1, ss_col2 = st.columns(2)
    if "ss_mde_w" not in st.session_state:
        st.session_state["ss_mde_w"] = float(st.session_state.get("ss_mde", 10.0))
    if "ss_target_w" not in st.session_state:
        st.session_state["ss_target_w"] = float(st.session_state.get("ss_target", 0.95))
    with ss_col1:
        ss_mde = st.slider("Relative MDE to detect (%)", 2.0, 30.0, step=1.0, key="ss_mde_w")
    with ss_col2:
        ss_target = st.slider("Target P(best)", 0.80, 0.99, step=0.01, key="ss_target_w")
    st.session_state["ss_mde"] = ss_mde
    st.session_state["ss_target"] = ss_target
    if st.button("Run sample size simulation"):
        ss = run_bayes_sample_size(
            df, prior_alpha=prior_alpha, prior_beta=prior_beta,
            mde_relative_pct=ss_mde, target_prob_best=ss_target,
        )
        st.markdown(
            f"To detect a **{ss.mde_relative_pct:.0f}%** relative lift from a "
            f"**{fmt_pct(ss.baseline_rate)}** baseline with "
            f"**P(best) ≥ {ss.target_prob_best:.0%}**:"
        )
        st.metric("Recommended n per group", f"{ss.recommended_n:,}")
        st.caption(ss.note)
    st.caption(
        "Note: the simulation is seeded, so the same data + prior + assumptions "
        "always give the same answer – it changes when any of those change."
    )

sidebar_data_status()