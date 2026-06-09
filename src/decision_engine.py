import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional


# result dataclasses

@dataclass
class RevenueImpact:
    control_rate:              float
    treatment_rate:            float
    absolute_lift:             float
    relative_lift_pct:         float
    revenue_per_conversion:    float
    daily_visitors:            int
    traffic_split:             float

    # daily impact
    control_daily_conversions:   float
    treatment_daily_conversions: float
    daily_conversion_lift:       float
    daily_revenue_lift:          float

    # annualised
    annual_revenue_lift:         float
    annual_revenue_lift_low:     float   # conservative (lower CI bound)
    annual_revenue_lift_high:    float   # optimistic  (upper CI bound)


@dataclass
class RiskReward:
    prob_treatment_better:     float    # from Bayesian engine
    expected_loss_if_wrong:    float    # expected loss (treatment) from Bayesian
    revenue_per_conversion:    float
    daily_visitors:            int

    # expected value of each decision
    ev_ship_treatment:         float
    ev_keep_control:           float
    ev_recommended_action:     str

    # risk-adjusted metrics
    downside_daily_revenue:    float    # daily loss if treatment is actually worse
    upside_daily_revenue:      float    # daily gain if treatment is actually better
    reward_to_risk_ratio:      float


@dataclass
class ScenarioAnalysis:
    scenario:                  str
    assumed_lift_pct:          float
    daily_revenue_impact:      float
    annual_revenue_impact:     float
    probability:               float
    recommendation:            str


@dataclass
class DecisionSummary:
    recommendation:            str      # "SHIP" | "DO NOT SHIP" | "CONTINUE TESTING"
    confidence:                str      # "HIGH" | "MEDIUM" | "LOW"
    rationale:                 list[str]
    primary_metric_significant: bool
    prob_treatment_better:     float
    expected_annual_uplift:    float
    risk_rating:               str      # "LOW" | "MEDIUM" | "HIGH"


# main engine

class DecisionEngine:
    """
    Translates statistical results into business decisions.

    Takes outputs from StatsEngine and BayesianEngine and computes:
    - Revenue impact (daily + annual, with CI bounds)
    - Risk/reward analysis
    - Scenario analysis (pessimistic / base / optimistic)
    - Final decision recommendation with rationale
    """

    def __init__(
        self,
        stats_result,        # ProportionTestResult from StatsEngine
        bayesian_result,     # BayesianResult from BayesianEngine
        revenue_per_conversion: float = 45.0,
        daily_visitors:      int   = 5_000,
        traffic_split:       float = 0.5,    # fraction in each arm
    ):
        self.stats    = stats_result
        self.bayes    = bayesian_result
        self.rev_per_conv   = revenue_per_conversion
        self.daily_visitors = daily_visitors
        self.traffic_split  = traffic_split

    # revenue impact

    def revenue_impact(self) -> RevenueImpact:
        ctrl_rate = self.stats.control_rate
        trt_rate  = self.stats.treatment_rate
        abs_lift  = trt_rate - ctrl_rate

        visitors_per_arm = self.daily_visitors * self.traffic_split

        ctrl_daily_conv = visitors_per_arm * ctrl_rate
        trt_daily_conv  = visitors_per_arm * trt_rate
        daily_conv_lift = trt_daily_conv - ctrl_daily_conv
        daily_rev_lift  = daily_conv_lift * self.rev_per_conv

        annual_rev_lift = daily_rev_lift * 365

        # CI-based bounds using treatment CI from stats engine
        trt_rate_low  = self.stats.treatment_ci[0]
        trt_rate_high = self.stats.treatment_ci[1]

        annual_low  = (visitors_per_arm * (trt_rate_low  - ctrl_rate)) * self.rev_per_conv * 365
        annual_high = (visitors_per_arm * (trt_rate_high - ctrl_rate)) * self.rev_per_conv * 365

        return RevenueImpact(
            control_rate=ctrl_rate,
            treatment_rate=trt_rate,
            absolute_lift=abs_lift,
            relative_lift_pct=self.stats.relative_lift_pct,
            revenue_per_conversion=self.rev_per_conv,
            daily_visitors=self.daily_visitors,
            traffic_split=self.traffic_split,
            control_daily_conversions=ctrl_daily_conv,
            treatment_daily_conversions=trt_daily_conv,
            daily_conversion_lift=daily_conv_lift,
            daily_revenue_lift=daily_rev_lift,
            annual_revenue_lift=annual_rev_lift,
            annual_revenue_lift_low=annual_low,
            annual_revenue_lift_high=annual_high,
        )

    # risk / reward

    def risk_reward(self) -> RiskReward:
        prob_better = self.bayes.prob_treatment_better
        prob_worse  = 1 - prob_better

        visitors_per_arm = self.daily_visitors * self.traffic_split

        # expected value of shipping treatment
        # = P(better) * daily uplift - P(worse) * daily downside
        obs_lift       = self.stats.treatment_rate - self.stats.control_rate
        daily_upside   = visitors_per_arm * obs_lift * self.rev_per_conv
        daily_downside = visitors_per_arm * abs(obs_lift) * self.rev_per_conv  # symmetric assumption

        ev_ship    = (prob_better * daily_upside) - (prob_worse * daily_downside)
        ev_keep    = 0.0  # status quo = no change

        reward_to_risk = daily_upside / daily_downside if daily_downside > 0 else float("inf")

        recommended = "SHIP" if ev_ship > ev_keep else "KEEP CONTROL"

        return RiskReward(
            prob_treatment_better=prob_better,
            expected_loss_if_wrong=self.bayes.expected_loss_treatment,
            revenue_per_conversion=self.rev_per_conv,
            daily_visitors=self.daily_visitors,
            ev_ship_treatment=ev_ship,
            ev_keep_control=ev_keep,
            ev_recommended_action=recommended,
            downside_daily_revenue=daily_downside,
            upside_daily_revenue=daily_upside,
            reward_to_risk_ratio=reward_to_risk,
        )

    # scenario analysis

    def scenario_analysis(self) -> list[ScenarioAnalysis]:
        """
        Three scenarios: pessimistic (lower CI), base (observed), optimistic (upper CI).
        Also includes a null scenario (no real effect).
        """
        ctrl_rate        = self.stats.control_rate
        visitors_per_arm = self.daily_visitors * self.traffic_split

        scenarios_raw = [
            ("Null (no effect)",  0.0,                                          0.05),
            ("Pessimistic",       self.stats.treatment_ci[0] - ctrl_rate,       0.10),
            ("Base case",         self.stats.treatment_rate  - ctrl_rate,       0.65),
            ("Optimistic",        self.stats.treatment_ci[1] - ctrl_rate,       0.20),
        ]

        results = []
        for name, lift, prob in scenarios_raw:
            daily  = visitors_per_arm * lift * self.rev_per_conv
            annual = daily * 365

            if lift <= 0:
                rec = "Do not ship"
            elif lift < ctrl_rate * 0.05:
                rec = "Continue testing"
            else:
                rec = "Ship treatment"

            results.append(ScenarioAnalysis(
                scenario=name,
                assumed_lift_pct=lift * 100,
                daily_revenue_impact=daily,
                annual_revenue_impact=annual,
                probability=prob,
                recommendation=rec,
            ))

        return results

    # final decision 

    def final_decision(self) -> DecisionSummary:
        prob_better  = self.bayes.prob_treatment_better
        significant  = self.stats.significant
        rel_lift     = self.stats.relative_lift_pct
        impact       = self.revenue_impact()
        rr           = self.risk_reward()

        rationale = []

        # determine recommendation
        if prob_better >= 0.95 and significant:
            recommendation = "SHIP"
            confidence     = "HIGH"
            risk_rating    = "LOW"
            rationale.append(f"P(treatment best) = {prob_better*100:.1f}% exceeds 95% threshold")
            rationale.append(f"Frequentist test significant at α=0.05 (p={self.stats.p_value:.4f})")
            rationale.append(f"Relative lift of {rel_lift:.1f}% is meaningful")
            rationale.append(f"Expected annual revenue uplift: ${impact.annual_revenue_lift:,.0f}")

        elif prob_better >= 0.80 and significant:
            recommendation = "SHIP"
            confidence     = "MEDIUM"
            risk_rating    = "MEDIUM"
            rationale.append(f"P(treatment best) = {prob_better*100:.1f}% – strong but below 95%")
            rationale.append(f"Frequentist test significant (p={self.stats.p_value:.4f})")
            rationale.append(f"Consider monitoring post-launch for 1–2 weeks")

        elif prob_better >= 0.80 and not significant:
            recommendation = "CONTINUE TESTING"
            confidence     = "LOW"
            risk_rating    = "MEDIUM"
            rationale.append(f"Bayesian probability {prob_better*100:.1f}% is promising")
            rationale.append("Frequentist test not yet significant – need more data")
            rationale.append(f"Recommend running until n ≥ {int(self.daily_visitors * 6):,} total visitors")

        elif prob_better < 0.50:
            recommendation = "DO NOT SHIP"
            confidence     = "HIGH"
            risk_rating    = "LOW"
            rationale.append(f"P(treatment best) = {prob_better*100:.1f}% – treatment likely worse")
            rationale.append("Shipping would likely hurt revenue")

        else:
            recommendation = "CONTINUE TESTING"
            confidence     = "LOW"
            risk_rating    = "HIGH"
            rationale.append("Results are inconclusive – insufficient evidence either way")
            rationale.append("Extend experiment or increase sample size")

        # add EV note
        rationale.append(
            f"Expected value of shipping: ${rr.ev_ship_treatment:,.2f}/day "
            f"vs keeping control: ${rr.ev_keep_control:,.2f}/day"
        )

        return DecisionSummary(
            recommendation=recommendation,
            confidence=confidence,
            rationale=rationale,
            primary_metric_significant=significant,
            prob_treatment_better=prob_better,
            expected_annual_uplift=impact.annual_revenue_lift,
            risk_rating=risk_rating,
        )

    # scenario DataFrame (for Streamlit table)

    def scenario_df(self) -> pd.DataFrame:
        rows = self.scenario_analysis()
        return pd.DataFrame([{
            "Scenario":            r.scenario,
            "Assumed lift":        f"{r.assumed_lift_pct:+.3f}%",
            "Daily revenue impact": f"${r.daily_revenue_impact:,.2f}",
            "Annual revenue impact": f"${r.annual_revenue_impact:,.0f}",
            "Probability":         f"{r.probability*100:.0f}%",
            "Recommendation":      r.recommendation,
        } for r in rows])

    # full results dict (used by Streamlit pages)

    def run_all(self) -> dict:
        return {
            "revenue_impact":  self.revenue_impact(),
            "risk_reward":     self.risk_reward(),
            "scenarios":       self.scenario_df(),
            "decision":        self.final_decision(),
        }


# quick test

if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from src.experiment_simulator import load_or_simulate
    from src.stats_engine import StatsEngine
    from src.bayesian_engine import BayesianEngine
    import json

    with open("data/experiment_config.json") as f:
        config = json.load(f)

    df      = load_or_simulate()
    stats   = StatsEngine(df).test_conversion_rate()
    bayes   = BayesianEngine(df).analyse()

    engine  = DecisionEngine(
        stats_result=stats,
        bayesian_result=bayes,
        revenue_per_conversion=config["revenue_per_conversion"],
        daily_visitors=5000,
    )

    results = engine.run_all()

    rev = results["revenue_impact"]
    print("\n=== Revenue Impact ===")
    print(f"Daily conversion lift:   {rev.daily_conversion_lift:+.1f} conversions")
    print(f"Daily revenue lift:      ${rev.daily_revenue_lift:+,.2f}")
    print(f"Annual revenue lift:     ${rev.annual_revenue_lift:+,.0f}")
    print(f"  Conservative (low CI): ${rev.annual_revenue_lift_low:+,.0f}")
    print(f"  Optimistic  (high CI): ${rev.annual_revenue_lift_high:+,.0f}")

    rr = results["risk_reward"]
    print(f"\n=== Risk / Reward ===")
    print(f"P(treatment better):     {rr.prob_treatment_better*100:.1f}%")
    print(f"EV ship treatment:       ${rr.ev_ship_treatment:+,.2f}/day")
    print(f"EV keep control:         ${rr.ev_keep_control:,.2f}/day")
    print(f"Upside:                  ${rr.upside_daily_revenue:,.2f}/day")
    print(f"Downside:                ${rr.downside_daily_revenue:,.2f}/day")
    print(f"Reward-to-risk ratio:    {rr.reward_to_risk_ratio:.2f}x")
    print(f"Recommended action:      {rr.ev_recommended_action}")

    print(f"\n=== Scenario Analysis ===")
    print(results["scenarios"].to_string(index=False))

    dec = results["decision"]
    print(f"\n=== Final Decision ===")
    print(f"Recommendation:  {dec.recommendation}")
    print(f"Confidence:      {dec.confidence}")
    print(f"Risk rating:     {dec.risk_rating}")
    print(f"Annual uplift:   ${dec.expected_annual_uplift:,.0f}")
    print(f"\nRationale:")
    for point in dec.rationale:
        print(f"  • {point}")