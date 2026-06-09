import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta
from pathlib import Path


class ExperimentSimulator:
    """
    Generates synthetic A/B test data from experiment config parameters.
    Produces a realistic user-level dataset with conversions, revenue, and timestamps.
    """

    def __init__(self, config_path: str = "data/experiment_config.json"):
        self.config = self._load_config(config_path)
        self.rng = np.random.default_rng(seed=self.config.get("random_seed", 42))

    def _load_config(self, config_path: str) -> dict:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config not found at {config_path}")
        with open(path) as f:
            return json.load(f)

    def simulate(self, save: bool = True) -> pd.DataFrame:
        """
        Run the simulation and return a user-level DataFrame.

        Columns:
            user_id        - unique user identifier
            group          - 'control' or 'treatment'
            converted      - 1 if user converted, 0 otherwise
            revenue        - revenue generated (0 if no conversion)
            timestamp      - simulated event timestamp
            session_length - simulated session duration in seconds (covariate)
            device         - mobile / desktop / tablet (covariate)
        """
        n = self.config["sample_size_per_group"]
        control_rate = self.config["control_conversion_rate"]
        treatment_rate = self.config["treatment_conversion_rate"]
        rev_per_conversion = self.config["revenue_per_conversion"]

        control_df = self._generate_group(
            n=n,
            group_label="control",
            conversion_rate=control_rate,
            revenue_per_conversion=rev_per_conversion,
            id_offset=0,
        )

        treatment_df = self._generate_group(
            n=n,
            group_label="treatment",
            conversion_rate=treatment_rate,
            revenue_per_conversion=rev_per_conversion,
            id_offset=n,
        )

        df = pd.concat([control_df, treatment_df], ignore_index=True)
        df = df.sample(frac=1, random_state=42).reset_index(drop=True)  # shuffle

        if save:
            out_path = Path("data/simulated_ab_test.csv")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(out_path, index=False)
            print(f"Saved {len(df):,} rows to {out_path}")

        self._print_summary(df)
        return df

    def _generate_group(
        self,
        n: int,
        group_label: str,
        conversion_rate: float,
        revenue_per_conversion: float,
        id_offset: int,
    ) -> pd.DataFrame:

        user_ids = [f"user_{id_offset + i:05d}" for i in range(n)]
        conversions = self.rng.binomial(1, conversion_rate, size=n)

        # revenue: converted users get base rev + some noise
        revenue = np.where(
            conversions == 1,
            revenue_per_conversion * self.rng.uniform(0.7, 1.5, size=n),
            0.0,
        )

        # timestamps spread over 14 days
        start_date = datetime(2024, 1, 1)
        seconds_in_14_days = 14 * 24 * 3600
        timestamps = [
            start_date + timedelta(seconds=int(s))
            for s in self.rng.integers(0, seconds_in_14_days, size=n)
        ]

        # covariates
        session_lengths = self.rng.integers(30, 600, size=n)  # 30s to 10min
        devices = self.rng.choice(
            ["mobile", "desktop", "tablet"],
            size=n,
            p=[0.55, 0.35, 0.10],
        )

        return pd.DataFrame({
            "user_id": user_ids,
            "group": group_label,
            "converted": conversions,
            "revenue": np.round(revenue, 2),
            "timestamp": timestamps,
            "session_length_sec": session_lengths,
            "device": devices,
        })

    def _print_summary(self, df: pd.DataFrame) -> None:
        print("\n--- Experiment Summary ---")
        for group in ["control", "treatment"]:
            subset = df[df["group"] == group]
            n = len(subset)
            conversions = subset["converted"].sum()
            rate = conversions / n
            total_rev = subset["revenue"].sum()
            print(f"\n{group.capitalize()} (n={n:,})")
            print(f"  Conversions : {conversions:,}")
            print(f"  Conv. rate  : {rate:.4f} ({rate*100:.2f}%)")
            print(f"  Total rev   : ${total_rev:,.2f}")
        print("\n--------------------------\n")


def load_or_simulate(
    csv_path: str = "data/simulated_ab_test.csv",
    config_path: str = "data/experiment_config.json",
    force_resimulate: bool = False,
) -> pd.DataFrame:
    """
    Convenience function used by the Streamlit pages.
    Loads existing CSV if present, otherwise runs the simulator.
    """
    path = Path(csv_path)
    if path.exists() and not force_resimulate:
        df = pd.read_csv(path, parse_dates=["timestamp"])
        print(f"Loaded existing data: {len(df):,} rows from {csv_path}")
        return df

    print("No existing data found – running simulator...")
    sim = ExperimentSimulator(config_path=config_path)
    return sim.simulate(save=True)


if __name__ == "__main__":
    sim = ExperimentSimulator()
    df = sim.simulate(save=True)
    print(df.head(10).to_string(index=False))