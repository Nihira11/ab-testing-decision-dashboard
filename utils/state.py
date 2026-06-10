"""
Shared state + caching helpers for the Streamlit dashboard.

Keeps one DataFrame in st.session_state so every page analyses the same data,
and caches engine runs so switching pages is instant.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.experiment_simulator import ExperimentSimulator
from src.stats_engine import StatsEngine
from src.bayesian_engine import BayesianEngine
from src.decision_engine import DecisionEngine
from utils.data_loader import load_config, load_data
from utils.theme import inject_css


PAGE_KWARGS = dict(layout="wide", initial_sidebar_state="expanded")


# data 

def get_config() -> dict:
    if "config" not in st.session_state:
        st.session_state["config"] = load_config()
    return st.session_state["config"]


def get_df() -> pd.DataFrame:
    """Returns the active dataset (simulated by default, or an uploaded CSV)."""
    inject_css()  # styling applies on every page
    if "df" not in st.session_state:
        st.session_state["df"] = load_data()
        st.session_state["data_source"] = "Simulated demo data"
    return st.session_state["df"]


def set_df(df: pd.DataFrame, source: str) -> None:
    st.session_state["df"] = df
    st.session_state["data_source"] = source
    # results depend on the data – clear caches so everything recomputes
    run_stats.clear()
    run_bayes.clear()
    run_bayes_sample_size.clear()


def data_source() -> str:
    return st.session_state.get("data_source", "Simulated demo data")


DEMO_SCENARIOS = {
    "Clear winner (5.0% → 5.8%)":      0.058,
    "Marginal lift (5.0% → 5.2%)":     0.052,
    "No real effect (5.0% → 5.0%)":    0.050,
    "Treatment worse (5.0% → 4.6%)":   0.046,
}


def simulate_scenario(treatment_rate: float, seed: int = 42) -> pd.DataFrame:
    """Regenerate demo data with a different true treatment effect,
    so the decision engine's other recommendations can be demonstrated."""
    sim = ExperimentSimulator()
    sim.config["treatment_conversion_rate"] = treatment_rate
    sim.config["random_seed"] = seed
    import numpy as np
    sim.rng = np.random.default_rng(seed=seed)
    return sim.simulate(save=False)


# cached engine runs 

@st.cache_data(show_spinner="Running frequentist tests...")
def run_stats(
    df: pd.DataFrame,
    alpha: float = 0.05,
    mde_relative_pct: float = 10.0,
    target_power: float = 0.80,
) -> dict:
    engine = StatsEngine(df, alpha=alpha)
    return {
        "summary":    engine.summary_df(),
        "conversion": engine.test_conversion_rate(),
        "revenue":    engine.test_revenue_per_user(),
        "power":      engine.power_analysis(
            mde_relative_pct=mde_relative_pct, target_power=target_power),
        # real-world uploads may not have a device column
        "chi_square": engine.chi_square_segment("device") if "device" in df.columns else None,
    }


@st.cache_data(show_spinner="Sampling posteriors...")
def run_bayes(df: pd.DataFrame, prior_alpha: float = 1.0, prior_beta: float = 1.0) -> dict:
    """Fast Bayesian results (posteriors, P(best), uplift). Excludes the slow
    sample-size simulation – use run_bayes_sample_size for that."""
    engine = BayesianEngine(df, prior_alpha=prior_alpha, prior_beta=prior_beta)
    return {
        "result":      engine.analyse(),
        "curves":      engine.posterior_curves(),
        "uplift_dist": engine.uplift_distribution(),
    }


@st.cache_data(show_spinner="Simulating required sample size (this one takes a moment)...")
def run_bayes_sample_size(
    df: pd.DataFrame,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
    mde_relative_pct: float = 10.0,
    target_prob_best: float = 0.95,
):
    engine = BayesianEngine(df, prior_alpha=prior_alpha, prior_beta=prior_beta)
    return engine.estimate_sample_size(
        mde_relative_pct=mde_relative_pct,
        target_prob_best=target_prob_best,
    )


def run_decision(
    stats_result,
    bayes_result,
    revenue_per_conversion: float,
    daily_visitors: int,
    traffic_split: float = 0.5,
) -> dict:
    """Decision engine is cheap – no caching needed, just re-run with current inputs."""
    return DecisionEngine(
        stats_result=stats_result,
        bayesian_result=bayes_result,
        revenue_per_conversion=revenue_per_conversion,
        daily_visitors=daily_visitors,
        traffic_split=traffic_split,
    ).run_all()


# sidebar

def sidebar_data_status() -> None:
    """Small data status block shown at the bottom of every page's sidebar."""
    df = get_df()
    with st.sidebar:
        st.divider()
        st.caption(f"**Data:** {data_source()}")
        st.caption(f"{len(df):,} users · {df['converted'].sum():,} conversions")
        if st.button("Reset to demo data", use_container_width=True):
            set_df(load_data(force_resimulate=False), "Simulated demo data")
            st.rerun()