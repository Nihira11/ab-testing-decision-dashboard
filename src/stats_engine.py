import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest, proportion_confint
from statsmodels.stats.power import NormalIndPower, TTestIndPower
from dataclasses import dataclass, field
from typing import Optional


# result dataclasses

@dataclass
class ProportionTestResult:
    test_type:            str
    control_conversions:  int
    control_n:            int
    treatment_conversions: int
    treatment_n:          int
    control_rate:         float
    treatment_rate:       float
    absolute_lift:        float
    relative_lift_pct:    float
    z_statistic:          float
    p_value:              float
    significant:          bool
    alpha:                float
    control_ci:           tuple[float, float]
    treatment_ci:         tuple[float, float]
    pooled_se:            float


@dataclass
class MeanTestResult:
    test_type:         str
    control_mean:      float
    treatment_mean:    float
    control_std:       float
    treatment_std:     float
    control_n:         int
    treatment_n:       int
    absolute_lift:     float
    relative_lift_pct: float
    t_statistic:       float
    p_value:           float
    significant:       bool
    alpha:             float
    cohens_d:          float
    control_ci:        tuple[float, float]
    treatment_ci:      tuple[float, float]


@dataclass
class PowerAnalysisResult:
    baseline_rate:       float
    mde_relative_pct:    float
    mde_absolute:        float
    required_n_per_group: int
    current_n_per_group: int
    achieved_power:      float
    alpha:               float
    is_underpowered:     bool


@dataclass
class SummaryStats:
    group:       str
    n:           int
    conversions: int
    conv_rate:   float
    mean_revenue: float
    total_revenue: float
    std_revenue:  float
    median_revenue: float


# main engine

class StatsEngine:
    """
    Frequentist A/B testing engine.
    Accepts a user-level DataFrame with columns:
        group, converted, revenue
    """

    def __init__(self, df: pd.DataFrame, alpha: float = 0.05):
        self._validate(df)
        self.df = df.copy()
        self.alpha = alpha

        self.control   = df[df["group"] == "control"]
        self.treatment = df[df["group"] == "treatment"]

    def _validate(self, df: pd.DataFrame) -> None:
        required = {"group", "converted", "revenue"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"DataFrame missing columns: {missing}")
        if set(df["group"].unique()) != {"control", "treatment"}:
            raise ValueError("group column must contain 'control' and 'treatment' only")

    # summary stats

    def summary_stats(self) -> list[SummaryStats]:
        results = []
        for group_label, subset in [("control", self.control), ("treatment", self.treatment)]:
            n = len(subset)
            conversions = subset["converted"].sum()
            results.append(SummaryStats(
                group=group_label,
                n=n,
                conversions=int(conversions),
                conv_rate=conversions / n,
                mean_revenue=subset["revenue"].mean(),
                total_revenue=subset["revenue"].sum(),
                std_revenue=subset["revenue"].std(),
                median_revenue=subset["revenue"].median(),
            ))
        return results

    def summary_df(self) -> pd.DataFrame:
        rows = self.summary_stats()
        return pd.DataFrame([vars(r) for r in rows])

    # conversion rate test (two-proportion z-test)

    def test_conversion_rate(self) -> ProportionTestResult:
        ctrl_conv = int(self.control["converted"].sum())
        trt_conv  = int(self.treatment["converted"].sum())
        ctrl_n    = len(self.control)
        trt_n     = len(self.treatment)

        ctrl_rate = ctrl_conv / ctrl_n
        trt_rate  = trt_conv  / trt_n

        counts = np.array([trt_conv, ctrl_conv])
        nobs   = np.array([trt_n,    ctrl_n])

        z_stat, p_value = proportions_ztest(counts, nobs, alternative="two-sided")

        ctrl_ci = proportion_confint(ctrl_conv, ctrl_n, alpha=self.alpha, method="wilson")
        trt_ci  = proportion_confint(trt_conv,  trt_n,  alpha=self.alpha, method="wilson")

        pooled_p  = (ctrl_conv + trt_conv) / (ctrl_n + trt_n)
        pooled_se = np.sqrt(pooled_p * (1 - pooled_p) * (1/ctrl_n + 1/trt_n))

        return ProportionTestResult(
            test_type="Two-proportion z-test",
            control_conversions=ctrl_conv,
            control_n=ctrl_n,
            treatment_conversions=trt_conv,
            treatment_n=trt_n,
            control_rate=ctrl_rate,
            treatment_rate=trt_rate,
            absolute_lift=trt_rate - ctrl_rate,
            relative_lift_pct=((trt_rate - ctrl_rate) / ctrl_rate) * 100,
            z_statistic=float(z_stat),
            p_value=float(p_value),
            significant=p_value < self.alpha,
            alpha=self.alpha,
            control_ci=ctrl_ci,
            treatment_ci=trt_ci,
            pooled_se=float(pooled_se),
        )

    # revenue per user test (Welch's t-test)

    def test_revenue_per_user(self) -> MeanTestResult:
        ctrl_rev = self.control["revenue"].values
        trt_rev  = self.treatment["revenue"].values

        t_stat, p_value = stats.ttest_ind(trt_rev, ctrl_rev, equal_var=False)

        ctrl_mean, trt_mean = ctrl_rev.mean(), trt_rev.mean()
        ctrl_std, trt_std = ctrl_rev.std(ddof=1), trt_rev.std(ddof=1)
        ctrl_n,    trt_n    = len(ctrl_rev),   len(trt_rev)

        # Cohen's d (pooled std)
        pooled_std = np.sqrt((ctrl_std**2 + trt_std**2) / 2)
        cohens_d   = (trt_mean - ctrl_mean) / pooled_std if pooled_std > 0 else 0.0

        # 95% CIs on the means
        ctrl_se = stats.sem(ctrl_rev)
        trt_se  = stats.sem(trt_rev)
        t_crit  = stats.t.ppf(1 - self.alpha / 2, df=ctrl_n - 1)

        ctrl_ci = (ctrl_mean - t_crit * ctrl_se, ctrl_mean + t_crit * ctrl_se)
        trt_ci  = (trt_mean  - t_crit * trt_se,  trt_mean  + t_crit * trt_se)

        return MeanTestResult(
            test_type="Welch's t-test (revenue per user)",
            control_mean=ctrl_mean,
            treatment_mean=trt_mean,
            control_std=ctrl_std,
            treatment_std=trt_std,
            control_n=ctrl_n,
            treatment_n=trt_n,
            absolute_lift=trt_mean - ctrl_mean,
            relative_lift_pct=((trt_mean - ctrl_mean) / ctrl_mean) * 100 if ctrl_mean > 0 else 0.0,
            t_statistic=float(t_stat),
            p_value=float(p_value),
            significant=p_value < self.alpha,
            alpha=self.alpha,
            cohens_d=float(cohens_d),
            control_ci=ctrl_ci,
            treatment_ci=trt_ci,
        )

    # power analysis

    def power_analysis(
        self,
        mde_relative_pct: float = 10.0,
        target_power: float = 0.80,
    ) -> PowerAnalysisResult:
        ctrl_rate = self.control["converted"].mean()
        mde_abs   = ctrl_rate * (mde_relative_pct / 100)
        effect_rate = ctrl_rate + mde_abs

        # effect size for proportions (Cohen's h)
        h = 2 * np.arcsin(np.sqrt(effect_rate)) - 2 * np.arcsin(np.sqrt(ctrl_rate))
        required_n = int(np.ceil(
            NormalIndPower().solve_power(
                effect_size=abs(h),
                alpha=self.alpha,
                power=target_power,
                alternative="two-sided",
            )
        ))

        # achieved power with current sample
        current_n    = len(self.control)
        achieved_pwr = NormalIndPower().solve_power(
            effect_size=abs(h),
            alpha=self.alpha,
            nobs1=current_n,
            alternative="two-sided",
        )

        return PowerAnalysisResult(
            baseline_rate=ctrl_rate,
            mde_relative_pct=mde_relative_pct,
            mde_absolute=mde_abs,
            required_n_per_group=required_n,
            current_n_per_group=current_n,
            achieved_power=float(achieved_pwr),
            alpha=self.alpha,
            is_underpowered=achieved_pwr < target_power,
        )

    # chi-square test (device / segment breakdown)

    def chi_square_segment(self, segment_col: str = "device") -> dict:
        if segment_col not in self.df.columns:
            raise ValueError(f"Column '{segment_col}' not in DataFrame")

        contingency = pd.crosstab(
            self.df[segment_col],
            self.df["converted"],
        )
        chi2, p_value, dof, expected = stats.chi2_contingency(contingency)

        return {
            "test_type": "Chi-square test of independence",
            "segment_col": segment_col,
            "chi2_statistic": float(chi2),
            "p_value": float(p_value),
            "degrees_of_freedom": int(dof),
            "significant": p_value < self.alpha,
            "contingency_table": contingency,
        }

    # full results dict (used by Streamlit pages)

    def run_all(self) -> dict:
        return {
            "summary":    self.summary_df(),
            "conversion": self.test_conversion_rate(),
            "revenue":    self.test_revenue_per_user(),
            "power":      self.power_analysis(),
            "chi_square": self.chi_square_segment("device"),
        }


# quick test

if __name__ == "__main__":
    from experiment_simulator import load_or_simulate

    df = load_or_simulate()
    engine = StatsEngine(df)
    results = engine.run_all()

    print("\n=== Summary Stats ===")
    print(results["summary"].to_string(index=False))

    conv = results["conversion"]
    print(f"\n=== Conversion Rate Test ===")
    print(f"Control:   {conv.control_rate:.4f}  ({conv.control_rate*100:.2f}%)")
    print(f"Treatment: {conv.treatment_rate:.4f}  ({conv.treatment_rate*100:.2f}%)")
    print(f"Absolute lift:  {conv.absolute_lift:+.4f}")
    print(f"Relative lift:  {conv.relative_lift_pct:+.2f}%")
    print(f"Z-statistic:    {conv.z_statistic:.4f}")
    print(f"P-value:        {conv.p_value:.4f}")
    print(f"Significant:    {conv.significant}  (alpha={conv.alpha})")
    print(f"Control CI:     [{conv.control_ci[0]:.4f}, {conv.control_ci[1]:.4f}]")
    print(f"Treatment CI:   [{conv.treatment_ci[0]:.4f}, {conv.treatment_ci[1]:.4f}]")

    rev = results["revenue"]
    print(f"\n=== Revenue per User Test ===")
    print(f"Control mean:   ${rev.control_mean:.4f}")
    print(f"Treatment mean: ${rev.treatment_mean:.4f}")
    print(f"Absolute lift:  ${rev.absolute_lift:+.4f}")
    print(f"T-statistic:    {rev.t_statistic:.4f}")
    print(f"P-value:        {rev.p_value:.4f}")
    print(f"Cohen's d:      {rev.cohens_d:.4f}")
    print(f"Significant:    {rev.significant}")

    pwr = results["power"]
    print(f"\n=== Power Analysis (MDE={pwr.mde_relative_pct}%) ===")
    print(f"Required n per group: {pwr.required_n_per_group:,}")
    print(f"Current  n per group: {pwr.current_n_per_group:,}")
    print(f"Achieved power:       {pwr.achieved_power:.4f}")
    print(f"Underpowered:         {pwr.is_underpowered}")

    chi = results["chi_square"]
    print(f"\n=== Chi-Square (device) ===")
    print(f"Chi2: {chi['chi2_statistic']:.4f}  p={chi['p_value']:.4f}  significant={chi['significant']}")