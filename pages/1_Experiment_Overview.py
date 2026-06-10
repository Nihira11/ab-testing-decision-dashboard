"""Page 1 – Experiment Overview: data health, sample sizes, SRM check, segments."""

import sys
from pathlib import Path

import streamlit as st
from scipy import stats as sps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.state import PAGE_KWARGS, get_config, get_df, run_stats, sidebar_data_status
from utils.data_loader import get_sample_sizes, get_date_range, get_device_breakdown
from utils.formatting import fmt_pct, fmt_pvalue
from utils.plotting import (
    plot_conversions_over_time,
    plot_device_breakdown,
    plot_revenue_distribution,
)

st.set_page_config(page_title="Experiment Overview", page_icon="🧪", **PAGE_KWARGS)

config = get_config()
df = get_df()

st.title("Experiment Overview")
st.caption(f"**{config['experiment_name']}** – {config.get('hypothesis', '')}")

# sample sizes + SRM check 

sizes = get_sample_sizes(df)
dates = get_date_range(df)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total users", f"{sizes['total']:,}")
c2.metric("Control", f"{sizes['control']:,}")
c3.metric("Treatment", f"{sizes['treatment']:,}")
c4.metric("Duration", f"{dates['days']} days" if dates else "–")

st.subheader("Sample Ratio Mismatch (SRM) check")
st.markdown(
    "Before trusting any results, verify the randomisation actually delivered the "
    "intended 50/50 split. A significant SRM usually means a bug in assignment or "
    "logging – and invalidates the experiment."
)

n_ctrl, n_trt = sizes["control"], sizes["treatment"]
srm = sps.chisquare([n_ctrl, n_trt], f_exp=[sizes["total"] / 2, sizes["total"] / 2])

s1, s2, s3 = st.columns(3)
s1.metric("Observed split", f"{n_ctrl / sizes['total'] * 100:.2f}% / {n_trt / sizes['total'] * 100:.2f}%")
s2.metric("Chi-square", f"{srm.statistic:.4f}")
s3.metric("SRM p-value", f"{srm.pvalue:.4f}")

if srm.pvalue < 0.001:
    st.error("⚠️ Sample ratio mismatch detected (p < 0.001). Do **not** trust these results – investigate the assignment mechanism.")
else:
    st.success("No sample ratio mismatch – the split is consistent with 50/50 randomisation.")

# summary stats

st.subheader("Group summary")

summary = run_stats(df)["summary"].copy()
summary["conv_rate"] = summary["conv_rate"].map(lambda v: fmt_pct(v))
summary["mean_revenue"] = summary["mean_revenue"].map(lambda v: f"${v:,.2f}")
summary["total_revenue"] = summary["total_revenue"].map(lambda v: f"${v:,.0f}")
summary["std_revenue"] = summary["std_revenue"].map(lambda v: f"${v:,.2f}")
summary["median_revenue"] = summary["median_revenue"].map(lambda v: f"${v:,.2f}")
summary.columns = ["Group", "Users", "Conversions", "Conv. rate", "Mean revenue/user",
                   "Total revenue", "Std revenue", "Median revenue"]
st.dataframe(summary, use_container_width=True, hide_index=True)

# trends + segments

st.subheader("Conversion rate over time")
st.markdown(
    "Day-to-day stability matters: a treatment that only wins on some days may be "
    "interacting with a campaign, weekday effect, or novelty effect."
)
st.plotly_chart(plot_conversions_over_time(df), use_container_width=True)

device_df = get_device_breakdown(df)
extra_charts = []
if device_df is not None:
    extra_charts.append(plot_device_breakdown(device_df))
if df["revenue"].abs().sum() > 0:
    extra_charts.append(plot_revenue_distribution(df))

if extra_charts:
    cols = st.columns(len(extra_charts))
    for col, fig in zip(cols, extra_charts):
        with col:
            st.plotly_chart(fig, use_container_width=True)

sidebar_data_status()