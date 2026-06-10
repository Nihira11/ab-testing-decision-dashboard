"""Page 5 – Report Summary: one-page summary with markdown export."""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.report_generator import generate_markdown_report, generate_pdf_report
from utils.state import (
    PAGE_KWARGS, get_config, get_df, run_stats, run_bayes, run_decision,
    sidebar_data_status,
)
from utils.data_loader import get_sample_sizes, get_date_range

st.set_page_config(page_title="Report Summary", page_icon="📄", **PAGE_KWARGS)

config = get_config()
df = get_df()

st.title("Report Summary")
st.markdown(
    "Everything in one exportable page – built to be handed to a stakeholder "
    "who will never open the dashboard."
)
st.caption(
    f"Report reflects your current settings: α = {st.session_state.get('alpha', 0.05)}, "
    f"prior Beta({st.session_state.get('prior_alpha', 1.0):g}, {st.session_state.get('prior_beta', 1.0):g}), "
    "the active dataset, and the business assumptions in the sidebar."
)

# business inputs (mirrors Decision Centre defaults)

with st.sidebar:
    st.header("Business assumptions")
    if "rev_w_rs" not in st.session_state:
        st.session_state["rev_w_rs"] = float(st.session_state.get("rev_per_conv", config["revenue_per_conversion"]))
    if "vis_w_rs" not in st.session_state:
        st.session_state["vis_w_rs"] = int(st.session_state.get("daily_visitors", 5_000))
    if "split_w_rs" not in st.session_state:
        st.session_state["split_w_rs"] = float(st.session_state.get("traffic_split", 0.5))
    rev_per_conv = st.number_input(
        "Revenue per conversion ($)", min_value=0.0, step=5.0, key="rev_w_rs")
    daily_visitors = st.number_input(
        "Daily site visitors", min_value=100, step=500, key="vis_w_rs",
        help="Total daily traffic that would see the shipped variant.")
    traffic_split = st.slider(
        "Traffic share affected", 0.1, 1.0, step=0.05, key="split_w_rs",
        help="During the test only half of traffic sees treatment; after full rollout this is 100%.")
    st.session_state["rev_per_conv"] = rev_per_conv
    st.session_state["daily_visitors"] = daily_visitors
    st.session_state["traffic_split"] = traffic_split

alpha = st.session_state.get("alpha", 0.05)
prior_a = st.session_state.get("prior_alpha", 1.0)
prior_b = st.session_state.get("prior_beta", 1.0)

stats_results = run_stats(
    df, alpha=alpha,
    mde_relative_pct=st.session_state.get("mde", 10.0),
    target_power=st.session_state.get("target_power", 0.80),
)
bayes_results = run_bayes(df, prior_alpha=prior_a, prior_beta=prior_b)
decision_results = run_decision(
    stats_results["conversion"],
    bayes_results["result"],
    revenue_per_conversion=rev_per_conv,
    daily_visitors=int(daily_visitors),
    traffic_split=traffic_split,
)

sizes = get_sample_sizes(df)
dates = get_date_range(df)
data_info = {
    "total": sizes["total"],
    "control": sizes["control"],
    "treatment": sizes["treatment"],
    "days": dates["days"] if dates else None,
}

report_md = generate_markdown_report(
    config=config,
    stats_results=stats_results,
    bayes_results=bayes_results,
    decision_results=decision_results,
    data_info=data_info,
)

# export + display

report_pdf = generate_pdf_report(
    config=config,
    stats_results=stats_results,
    bayes_results=bayes_results,
    decision_results=decision_results,
    data_info=data_info,
)

from datetime import date
file_stem = f"AB_Test_Decision_Report_{date.today():%Y-%m-%d}"
col1, col2, col3 = st.columns([1, 1, 3])
with col1:
    st.download_button(
        "⬇️ Download PDF report",
        data=report_pdf,
        file_name=f"{file_stem}_report.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
with col2:
    st.download_button(
        "Download as markdown",
        data=report_md,
        file_name=f"{file_stem}_report.md",
        mime="text/markdown",
        use_container_width=True,
    )

st.divider()
st.markdown(report_md.replace("$", "\\$"))  # escape $ to avoid LaTeX rendering

sidebar_data_status()