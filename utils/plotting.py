"""
Plotly chart functions for the A/B Testing Dashboard.
Every function returns a plotly.graph_objects.Figure ready for st.plotly_chart().
All charts use the shared COLOURS palette from formatting.py.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.formatting import COLOURS


# shared layout defaults

def _base_layout(**kwargs) -> dict:
    """Base layout applied to every chart."""
    base = dict(
        font=dict(family="IBM Plex Sans, Inter, sans-serif", size=13, color="#33302E"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=60, r=40, t=60, b=95),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.28,
            xanchor="center",
            x=0.5,
        ),
    )
    base.update(kwargs)
    return base


def _add_gridlines(fig: go.Figure, axis: str = "y") -> go.Figure:
    update = dict(showgrid=True, gridcolor="#EBD9C7", gridwidth=1, zeroline=False)
    if axis in ("y", "both"):
        fig.update_yaxes(**update)
    if axis in ("x", "both"):
        fig.update_xaxes(**update)
    return fig


# 1. conversion rate bar chart

def plot_conversion_rates(conv_result) -> go.Figure:
    groups = ["Control", "Treatment"]
    rates  = [conv_result.control_rate * 100, conv_result.treatment_rate * 100]
    errors = [
        (conv_result.control_rate  - conv_result.control_ci[0])  * 100,
        (conv_result.treatment_rate - conv_result.treatment_ci[0]) * 100,
    ]
    colours = [COLOURS["control"], COLOURS["treatment"]]

    fig = go.Figure()
    for i, (group, rate, err, colour) in enumerate(zip(groups, rates, errors, colours)):
        fig.add_trace(go.Bar(
            name=group,
            x=[group],
            y=[rate],
            error_y=dict(type="data", array=[err], visible=True, color="#8E8478", thickness=1.5),
            marker_color=colour,
            width=0.4,
            text=f"{rate:.2f}%",
            textposition="outside",
        ))

    fig.update_layout(
        **_base_layout(title="Conversion Rate by Group"),
        yaxis_title="Conversion Rate (%)",
        showlegend=False,
        yaxis=dict(range=[0, max(rates) * 1.3]),
    )
    _add_gridlines(fig)
    return fig


# 2. conversion rate CI overlap chart

def plot_ci_overlap(conv_result) -> go.Figure:
    groups = ["Control", "Treatment"]
    means  = [conv_result.control_rate * 100,  conv_result.treatment_rate * 100]
    lows   = [conv_result.control_ci[0] * 100,  conv_result.treatment_ci[0] * 100]
    highs  = [conv_result.control_ci[1] * 100,  conv_result.treatment_ci[1] * 100]
    colours = [COLOURS["control"], COLOURS["treatment"]]

    fig = go.Figure()
    for i, (group, mean, low, high, colour) in enumerate(zip(groups, means, lows, highs, colours)):
        fig.add_trace(go.Scatter(
            x=[low, high],
            y=[group, group],
            mode="lines",
            line=dict(color=colour, width=3),
            showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=[mean],
            y=[group],
            mode="markers",
            marker=dict(color=colour, size=12, symbol="circle"),
            name=group,
            showlegend=True,
        ))
        for x_val in [low, high]:
            fig.add_trace(go.Scatter(
                x=[x_val, x_val],
                y=[i - 0.08, i + 0.08],
                mode="lines",
                line=dict(color=colour, width=2),
                showlegend=False,
            ))

    fig.update_layout(
        **_base_layout(title="95% Confidence Intervals"),
        xaxis_title="Conversion Rate (%)",
        yaxis=dict(categoryorder="array", categoryarray=groups),
    )
    _add_gridlines(fig, axis="x")
    return fig


# 3. posterior distribution overlay

def plot_posterior_distributions(curves_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    if curves_df["prior"].max() < 50:
        fig.add_trace(go.Scatter(
            x=curves_df["x"] * 100,
            y=curves_df["prior"],
            mode="lines",
            name="Prior",
            line=dict(color=COLOURS["prior"], width=1.5, dash="dot"),
            fill=None,
        ))

    fig.add_trace(go.Scatter(
        x=curves_df["x"] * 100,
        y=curves_df["control"],
        mode="lines",
        name="Control posterior",
        line=dict(color=COLOURS["control"], width=2.5),
        fill="tozeroy",
        fillcolor=f"rgba(15, 84, 153, 0.10)",
    ))

    fig.add_trace(go.Scatter(
        x=curves_df["x"] * 100,
        y=curves_df["treatment"],
        mode="lines",
        name="Treatment posterior",
        line=dict(color=COLOURS["treatment"], width=2.5),
        fill="tozeroy",
        fillcolor=f"rgba(153, 15, 61, 0.10)",
    ))

    fig.update_layout(
        **_base_layout(title="Posterior Distributions (Beta-Binomial)"),
        xaxis_title="Conversion Rate (%)",
        yaxis_title="Density",
    )
    _add_gridlines(fig)
    return fig


# 4. uplift distribution histogram

def plot_uplift_distribution(uplift_df: pd.DataFrame) -> go.Figure:
    uplift = uplift_df["uplift"].values * 100  # convert to %

    pos = uplift[uplift >= 0]
    neg = uplift[uplift <  0]

    fig = go.Figure()

    if len(neg) > 0:
        fig.add_trace(go.Histogram(
            x=neg,
            nbinsx=60,
            name="Treatment worse",
            marker_color=COLOURS["negative"],
            opacity=0.7,
        ))

    fig.add_trace(go.Histogram(
        x=pos,
        nbinsx=60,
        name="Treatment better",
        marker_color=COLOURS["positive"],
        opacity=0.7,
    ))

    fig.add_vline(x=0, line_width=1.5, line_dash="dash", line_color="#66605B")

    obs_lift = float(np.mean(uplift))
    fig.add_vline(
        x=obs_lift,
        line_width=1.5,
        line_dash="solid",
        line_color=COLOURS["highlight"],
        annotation_text=f"Mean: {obs_lift:+.3f}%",
        annotation_position="top right",
    )

    fig.update_layout(
        **_base_layout(title="Posterior Uplift Distribution (Treatment − Control)"),
        xaxis_title="Uplift in Conversion Rate (%)",
        yaxis_title="Frequency",
        barmode="overlay",
    )
    _add_gridlines(fig)
    return fig


# 5. revenue impact chart

def plot_revenue_impact(revenue_impact) -> go.Figure:
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Daily Revenue Lift", "Annual Revenue Lift"),
    )

    fig.add_trace(go.Bar(
        x=["Daily lift"],
        y=[revenue_impact.daily_revenue_lift],
        marker_color=COLOURS["positive"] if revenue_impact.daily_revenue_lift >= 0 else COLOURS["negative"],
        text=f"${revenue_impact.daily_revenue_lift:,.0f}",
        textposition="outside",
        showlegend=False,
    ), row=1, col=1)

    annual_mid   = revenue_impact.annual_revenue_lift
    annual_low   = revenue_impact.annual_revenue_lift_low
    annual_high  = revenue_impact.annual_revenue_lift_high
    error_minus  = annual_mid - annual_low
    error_plus   = annual_high - annual_mid

    fig.add_trace(go.Bar(
        x=["Annual lift"],
        y=[annual_mid],
        error_y=dict(
            type="data",
            array=[error_plus],
            arrayminus=[error_minus],
            visible=True,
            color="#8E8478",
            thickness=1.5,
        ),
        marker_color=COLOURS["positive"] if annual_mid >= 0 else COLOURS["negative"],
        text=f"${annual_mid:,.0f}",
        textposition="outside",
        showlegend=False,
    ), row=1, col=2)

    fig.update_layout(
        **_base_layout(title="Expected Revenue Impact"),
        yaxis_title="Revenue (USD)",
        yaxis2_title="Revenue (USD)",
    )
    _add_gridlines(fig)
    return fig


# 6. scenario analysis chart

def plot_scenario_analysis(scenarios_df: pd.DataFrame) -> go.Figure:
    annual_vals = (
        scenarios_df["Annual revenue impact"]
        .str.replace("[$,]", "", regex=True)
        .astype(float)
    )
    scenario_names = scenarios_df["Scenario"].tolist()
    probs          = scenarios_df["Probability"].tolist()

    colours = [
        COLOURS["negative"] if v < 0 else COLOURS["positive"]
        for v in annual_vals
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=annual_vals,
        y=scenario_names,
        orientation="h",
        marker_color=colours,
        text=[f"${v:,.0f}  ({p})" for v, p in zip(annual_vals, probs)],
        textposition="outside",
        showlegend=False,
    ))

    fig.add_vline(x=0, line_width=1, line_dash="solid", line_color="#66605B")

    fig.update_layout(
        **_base_layout(
            title="Scenario Analysis – Annual Revenue Impact",
            margin=dict(l=130, r=120, t=60, b=60),
        ),
        xaxis_title="Annual Revenue Impact (USD)",
        yaxis=dict(categoryorder="array", categoryarray=list(reversed(scenario_names))),
    )
    _add_gridlines(fig, axis="x")
    return fig


# 7. power curve

def plot_power_curve(stats_engine, mde_range: list = None) -> go.Figure:
    from statsmodels.stats.power import NormalIndPower

    if mde_range is None:
        mde_range = [5, 10, 15, 20]

    ctrl_rate = stats_engine.control["converted"].mean()
    n_values  = np.arange(1000, 50001, 500)

    fig = go.Figure()

    for mde_pct in mde_range:
        effect_rate = ctrl_rate * (1 + mde_pct / 100)
        h = 2 * np.arcsin(np.sqrt(effect_rate)) - 2 * np.arcsin(np.sqrt(ctrl_rate))

        powers = []
        for n in n_values:
            try:
                pwr = NormalIndPower().solve_power(
                    effect_size=abs(h),
                    alpha=stats_engine.alpha,
                    nobs1=n,
                    alternative="two-sided",
                )
                powers.append(min(float(pwr), 1.0))
            except Exception:
                powers.append(None)

        fig.add_trace(go.Scatter(
            x=n_values,
            y=powers,
            mode="lines",
            name=f"MDE = {mde_pct}%",
            line=dict(width=2),
        ))

    fig.add_hline(
        y=0.80,
        line_width=1.5,
        line_dash="dash",
        line_color="#66605B",
        annotation_text="80% power",
        annotation_position="right",
    )

    current_n = len(stats_engine.control)
    fig.add_vline(
        x=current_n,
        line_width=1.5,
        line_dash="dot",
        line_color=COLOURS["highlight"],
        annotation_text=f"Current n = {current_n:,}",
        annotation_position="top left",
    )

    fig.update_layout(
        **_base_layout(title="Power Curve by Sample Size and MDE"),
        xaxis_title="Sample Size per Group",
        yaxis_title="Statistical Power",
        yaxis=dict(range=[0, 1.05], tickformat=".0%"),
    )
    _add_gridlines(fig)
    return fig


# 8. device segment breakdown

def plot_device_breakdown(device_df: pd.DataFrame) -> go.Figure:
    devices  = device_df["device"].unique().tolist()
    ctrl_df  = device_df[device_df["group"] == "control"]
    trt_df   = device_df[device_df["group"] == "treatment"]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Control",
        x=ctrl_df["device"],
        y=ctrl_df["conv_rate"] * 100,
        marker_color=COLOURS["control"],
        text=[f"{v*100:.2f}%" for v in ctrl_df["conv_rate"]],
        textposition="outside",
    ))
    fig.add_trace(go.Bar(
        name="Treatment",
        x=trt_df["device"],
        y=trt_df["conv_rate"] * 100,
        marker_color=COLOURS["treatment"],
        text=[f"{v*100:.2f}%" for v in trt_df["conv_rate"]],
        textposition="outside",
    ))

    fig.update_layout(
        **_base_layout(title="Conversion Rate by Device"),
        xaxis_title="Device",
        yaxis_title="Conversion Rate (%)",
        barmode="group",
    )
    _add_gridlines(fig)
    return fig


# 9. conversions over time

def plot_conversions_over_time(df: pd.DataFrame) -> go.Figure:
    df = df.copy()
    df["date"] = pd.to_datetime(df["timestamp"]).dt.date

    daily = (
        df.groupby(["date", "group"])
        .agg(conversions=("converted", "sum"), n=("converted", "count"))
        .reset_index()
    )
    daily["conv_rate"] = daily["conversions"] / daily["n"] * 100

    fig = go.Figure()
    for group, colour in [("control", COLOURS["control"]), ("treatment", COLOURS["treatment"])]:
        subset = daily[daily["group"] == group].sort_values("date")
        fig.add_trace(go.Scatter(
            x=subset["date"],
            y=subset["conv_rate"],
            mode="lines+markers",
            name=group.capitalize(),
            line=dict(color=colour, width=2),
            marker=dict(size=5),
        ))

    fig.update_layout(
        **_base_layout(title="Daily Conversion Rate Over Time"),
        xaxis_title="Date",
        yaxis_title="Conversion Rate (%)",
    )
    _add_gridlines(fig)
    return fig


# 10. revenue distribution

def plot_revenue_distribution(df: pd.DataFrame) -> go.Figure:
    converters = df[df["converted"] == 1]
    ctrl_rev   = converters[converters["group"] == "control"]["revenue"]
    trt_rev    = converters[converters["group"] == "treatment"]["revenue"]

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=ctrl_rev,
        name="Control",
        marker_color=COLOURS["control"],
        opacity=0.65,
        nbinsx=40,
    ))
    fig.add_trace(go.Histogram(
        x=trt_rev,
        name="Treatment",
        marker_color=COLOURS["treatment"],
        opacity=0.65,
        nbinsx=40,
    ))

    fig.update_layout(
        **_base_layout(title="Revenue Distribution (Converters Only)"),
        xaxis_title="Revenue per User (USD)",
        yaxis_title="Count",
        barmode="overlay",
    )
    _add_gridlines(fig)
    return fig