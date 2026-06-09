import numpy as np
import pandas as pd
from scipy import stats
from dataclasses import dataclass


# result dataclasses

@dataclass
class BayesianResult:
    # data
    control_conversions:   int
    control_n:             int
    treatment_conversions: int
    treatment_n:           int

    # posterior parameters (Beta distribution)
    control_alpha:   float
    control_beta:    float
    treatment_alpha: float
    treatment_beta:  float

    # posterior means
    control_posterior_mean:   float
    treatment_posterior_mean: float

    # credible intervals (95%)
    control_credible_interval:   tuple[float, float]
    treatment_credible_interval: tuple[float, float]

    # key Bayesian metrics
    prob_treatment_better: float   # P(treatment > control)
    expected_loss_control: float   # expected loss if we keep control
    expected_loss_treatment: float # expected loss if we ship treatment
    relative_uplift_pct:   float

    # prior used
    prior_alpha: float
    prior_beta:  float


@dataclass
class SampleSizeResult:
    baseline_rate:        float
    mde_relative_pct:     float
    target_prob_best:     float
    recommended_n:        int
    note:                 str


# main engine

class BayesianEngine:
    """
    Bayesian A/B testing using a Beta-Binomial conjugate model.

    Prior: Beta(alpha, beta) – defaults to Beta(1,1) = uniform (no prior belief)
    Posterior: Beta(alpha + conversions, beta + non-conversions)

    No heavy dependencies – pure scipy.stats.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        prior_alpha: float = 1.0,
        prior_beta:  float = 1.0,
        n_samples:   int   = 100_000,
        random_seed: int   = 42,
    ):
        self._validate(df)
        self.df          = df.copy()
        self.prior_alpha = prior_alpha
        self.prior_beta  = prior_beta
        self.n_samples   = n_samples
        self.rng         = np.random.default_rng(random_seed)

        self.control   = df[df["group"] == "control"]
        self.treatment = df[df["group"] == "treatment"]

        # observed counts
        self.ctrl_conv  = int(self.control["converted"].sum())
        self.ctrl_n     = len(self.control)
        self.trt_conv   = int(self.treatment["converted"].sum())
        self.trt_n      = len(self.treatment)

        # posterior parameters
        self.ctrl_post_alpha  = prior_alpha + self.ctrl_conv
        self.ctrl_post_beta   = prior_beta  + (self.ctrl_n - self.ctrl_conv)
        self.trt_post_alpha   = prior_alpha + self.trt_conv
        self.trt_post_beta    = prior_beta  + (self.trt_n  - self.trt_conv)

    def _validate(self, df: pd.DataFrame) -> None:
        required = {"group", "converted"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"DataFrame missing columns: {missing}")
        if set(df["group"].unique()) != {"control", "treatment"}:
            raise ValueError("group column must contain 'control' and 'treatment' only")

    # posterior sampling

    def sample_posteriors(self) -> tuple[np.ndarray, np.ndarray]:
        """Draw samples from both posterior Beta distributions."""
        ctrl_samples = self.rng.beta(self.ctrl_post_alpha, self.ctrl_post_beta, size=self.n_samples)
        trt_samples  = self.rng.beta(self.trt_post_alpha,  self.trt_post_beta,  size=self.n_samples)
        return ctrl_samples, trt_samples

    # core analysis

    def analyse(self) -> BayesianResult:
        ctrl_samples, trt_samples = self.sample_posteriors()

        # posterior means (analytical)
        ctrl_mean = self.ctrl_post_alpha / (self.ctrl_post_alpha + self.ctrl_post_beta)
        trt_mean  = self.trt_post_alpha  / (self.trt_post_alpha  + self.trt_post_beta)

        # 95% credible intervals (HDI via percentile)
        ctrl_ci = (float(np.percentile(ctrl_samples, 2.5)),  float(np.percentile(ctrl_samples, 97.5)))
        trt_ci  = (float(np.percentile(trt_samples,  2.5)),  float(np.percentile(trt_samples,  97.5)))

        # P(treatment > control)
        prob_trt_better = float(np.mean(trt_samples > ctrl_samples))

        # expected loss
        # loss of choosing control = E[max(trt - ctrl, 0)]  (what we miss if trt is better)
        # loss of choosing treatment = E[max(ctrl - trt, 0)] (regret if ctrl was actually better)
        expected_loss_control   = float(np.mean(np.maximum(trt_samples - ctrl_samples, 0)))
        expected_loss_treatment = float(np.mean(np.maximum(ctrl_samples - trt_samples, 0)))

        relative_uplift = ((trt_mean - ctrl_mean) / ctrl_mean) * 100 if ctrl_mean > 0 else 0.0

        return BayesianResult(
            control_conversions=self.ctrl_conv,
            control_n=self.ctrl_n,
            treatment_conversions=self.trt_conv,
            treatment_n=self.trt_n,
            control_alpha=self.ctrl_post_alpha,
            control_beta=self.ctrl_post_beta,
            treatment_alpha=self.trt_post_alpha,
            treatment_beta=self.trt_post_beta,
            control_posterior_mean=float(ctrl_mean),
            treatment_posterior_mean=float(trt_mean),
            control_credible_interval=ctrl_ci,
            treatment_credible_interval=trt_ci,
            prob_treatment_better=prob_trt_better,
            expected_loss_control=expected_loss_control,
            expected_loss_treatment=expected_loss_treatment,
            relative_uplift_pct=float(relative_uplift),
            prior_alpha=self.prior_alpha,
            prior_beta=self.prior_beta,
        )

    # posterior PDF curves (for plotting)

    def posterior_curves(self, n_points: int = 500) -> pd.DataFrame:
        """
        Returns a DataFrame of x values and PDF densities for both posteriors.
        Used by plotting.py to draw the prior/posterior overlay chart.
        """
        # x range: cover both posteriors comfortably
        x_min = min(
            stats.beta.ppf(0.001, self.ctrl_post_alpha, self.ctrl_post_beta),
            stats.beta.ppf(0.001, self.trt_post_alpha,  self.trt_post_beta),
        )
        x_max = max(
            stats.beta.ppf(0.999, self.ctrl_post_alpha, self.ctrl_post_beta),
            stats.beta.ppf(0.999, self.trt_post_alpha,  self.trt_post_beta),
        )
        x = np.linspace(x_min, x_max, n_points)

        prior_pdf   = stats.beta.pdf(x, self.prior_alpha, self.prior_beta)
        ctrl_pdf    = stats.beta.pdf(x, self.ctrl_post_alpha,  self.ctrl_post_beta)
        trt_pdf     = stats.beta.pdf(x, self.trt_post_alpha,   self.trt_post_beta)

        return pd.DataFrame({
            "x":         x,
            "prior":     prior_pdf,
            "control":   ctrl_pdf,
            "treatment": trt_pdf,
        })

    # uplift distribution (for plotting)

    def uplift_distribution(self) -> pd.DataFrame:
        """
        Returns sampled uplift values (treatment - control) for histogram plotting.
        """
        ctrl_samples, trt_samples = self.sample_posteriors()
        uplift = trt_samples - ctrl_samples
        return pd.DataFrame({"uplift": uplift})

    # bayesian sample size estimate

    def estimate_sample_size(
        self,
        baseline_rate:    float = None,
        mde_relative_pct: float = 10.0,
        target_prob_best: float = 0.95,
        max_n:            int   = 100_000,
        step:             int   = 500,
    ) -> SampleSizeResult:
        """
        Estimates required n per group to achieve target P(treatment > control)
        via simulation – no closed-form solution exists for Bayesian power.
        Runs quickly by using small simulation batches.
        """
        if baseline_rate is None:
            baseline_rate = self.ctrl_conv / self.ctrl_n

        treatment_rate = baseline_rate * (1 + mde_relative_pct / 100)

        for n in range(500, max_n + 1, step):
            ctrl_conv_sim = int(round(baseline_rate  * n))
            trt_conv_sim  = int(round(treatment_rate * n))

            a_ctrl = self.prior_alpha + ctrl_conv_sim
            b_ctrl = self.prior_beta  + (n - ctrl_conv_sim)
            a_trt  = self.prior_alpha + trt_conv_sim
            b_trt  = self.prior_beta  + (n - trt_conv_sim)

            ctrl_s = self.rng.beta(a_ctrl, b_ctrl, size=20_000)
            trt_s  = self.rng.beta(a_trt,  b_trt,  size=20_000)
            prob   = np.mean(trt_s > ctrl_s)

            if prob >= target_prob_best:
                return SampleSizeResult(
                    baseline_rate=baseline_rate,
                    mde_relative_pct=mde_relative_pct,
                    target_prob_best=target_prob_best,
                    recommended_n=n,
                    note=f"Achieves P(treatment best) = {prob:.3f} at n={n:,} per group",
                )

        return SampleSizeResult(
            baseline_rate=baseline_rate,
            mde_relative_pct=mde_relative_pct,
            target_prob_best=target_prob_best,
            recommended_n=max_n,
            note=f"Target not reached within {max_n:,} – consider larger MDE or lower threshold",
        )

    # full results dict (used by Streamlit pages)

    def run_all(self) -> dict:
        result = self.analyse()
        return {
            "result":      result,
            "curves":      self.posterior_curves(),
            "uplift_dist": self.uplift_distribution(),
            "sample_size": self.estimate_sample_size(),
        }


# quick test

if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from src.experiment_simulator import load_or_simulate

    df = load_or_simulate()
    engine = BayesianEngine(df)
    results = engine.run_all()

    r = results["result"]
    print("\n=== Bayesian Analysis ===")
    print(f"Prior:               Beta({r.prior_alpha}, {r.prior_beta}) – uniform")
    print(f"\nControl  posterior:  Beta({r.control_alpha:.0f}, {r.control_beta:.0f})")
    print(f"  Mean:              {r.control_posterior_mean:.4f} ({r.control_posterior_mean*100:.2f}%)")
    print(f"  95% CI:            [{r.control_credible_interval[0]:.4f}, {r.control_credible_interval[1]:.4f}]")
    print(f"\nTreatment posterior: Beta({r.treatment_alpha:.0f}, {r.treatment_beta:.0f})")
    print(f"  Mean:              {r.treatment_posterior_mean:.4f} ({r.treatment_posterior_mean*100:.2f}%)")
    print(f"  95% CI:            [{r.treatment_credible_interval[0]:.4f}, {r.treatment_credible_interval[1]:.4f}]")
    print(f"\nP(treatment > control):    {r.prob_treatment_better:.4f} ({r.prob_treatment_better*100:.1f}%)")
    print(f"Expected loss (control):   {r.expected_loss_control:.6f}")
    print(f"Expected loss (treatment): {r.expected_loss_treatment:.6f}")
    print(f"Relative uplift:           {r.relative_uplift_pct:+.2f}%")

    ss = results["sample_size"]
    print(f"\n=== Bayesian Sample Size (MDE={ss.mde_relative_pct}%, target P={ss.target_prob_best}) ===")
    print(f"Recommended n per group: {ss.recommended_n:,}")
    print(f"Note: {ss.note}")

    curves = results["curves"]
    print(f"\n=== Posterior Curves ===")
    print(f"x range: [{curves['x'].min():.4f}, {curves['x'].max():.4f}]")
    print(f"Rows: {len(curves)}")
    print(curves.head(5).to_string(index=False))