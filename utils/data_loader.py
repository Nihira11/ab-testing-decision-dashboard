import pandas as pd
import json
import sys
from pathlib import Path

# make src importable when called from pages/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.experiment_simulator import load_or_simulate


# config

DEFAULT_CONFIG_PATH = Path("data/experiment_config.json")
DEFAULT_CSV_PATH    = Path("data/simulated_ab_test.csv")

REQUIRED_COLUMNS = {"user_id", "group", "converted", "timestamp"}  # revenue optional – filled with 0 if absent
REQUIRED_CONFIG_KEYS = {
    "experiment_name",
    "control_conversion_rate",
    "treatment_conversion_rate",
    "sample_size_per_group",
    "significance_level",
    "revenue_per_conversion",
}


# config loader

def load_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> dict:
    """Load and validate experiment_config.json."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path) as f:
        config = json.load(f)

    missing = REQUIRED_CONFIG_KEYS - set(config.keys())
    if missing:
        raise ValueError(f"Config missing required keys: {missing}")

    return config


# data loader

def load_data(
    csv_path:    str | Path = DEFAULT_CSV_PATH,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    force_resimulate: bool  = False,
) -> pd.DataFrame:
    """
    Load experiment data from CSV.
    Falls back to simulating if CSV doesn't exist.
    Validates schema and basic sanity checks.
    """
    df = load_or_simulate(
        csv_path=str(csv_path),
        config_path=str(config_path),
        force_resimulate=force_resimulate,
    )
    _validate_dataframe(df)
    return df


def load_uploaded_data(uploaded_file) -> pd.DataFrame:
    """
    Load and validate a user-uploaded CSV from Streamlit file_uploader.
    Returns cleaned DataFrame or raises ValueError with a user-friendly message.
    """
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        raise ValueError(f"Could not read CSV file: {e}")

    # normalise column names
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    # parse timestamp if present
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    # coerce boolean-ish converted values (True/False, yes/no) to 0/1
    if "converted" in df.columns and df["converted"].dtype != "int64":
        df["converted"] = (
            df["converted"]
            .map({True: 1, False: 0, "true": 1, "false": 0, "yes": 1, "no": 0,
                  "True": 1, "False": 0, 1: 1, 0: 0, "1": 1, "0": 0})
            .fillna(df["converted"])
        )
        df["converted"] = pd.to_numeric(df["converted"], errors="coerce").astype("Int64")

    # revenue is optional in real-world conversion datasets
    if "revenue" not in df.columns:
        df["revenue"] = 0.0

    _validate_dataframe(df)
    return df


# validation

def _validate_dataframe(df: pd.DataFrame) -> None:
    """Raise ValueError with a clear message if the DataFrame is invalid."""

    missing_cols = REQUIRED_COLUMNS - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"Dataset is missing required columns: {missing_cols}\n"
            f"Expected: {REQUIRED_COLUMNS}\n"
            f"Found:    {set(df.columns)}"
        )

    groups = set(df["group"].unique())
    if groups != {"control", "treatment"}:
        raise ValueError(
            f"'group' column must contain exactly 'control' and 'treatment'.\n"
            f"Found: {groups}"
        )

    conv_vals = set(df["converted"].unique())
    if not conv_vals.issubset({0, 1}):
        raise ValueError(
            f"'converted' column must be binary (0 or 1). Found values: {conv_vals}"
        )

    for g in ["control", "treatment"]:
        n = len(df[df["group"] == g])
        if n == 0:
            raise ValueError(f"Group '{g}' has no rows.")
        if n < 100:
            raise ValueError(
                f"Group '{g}' has only {n} rows – minimum 100 required for reliable results."
            )

    if (df["revenue"] < 0).any():
        raise ValueError("'revenue' column contains negative values.")


# convenience getters

def get_group(df: pd.DataFrame, group: str) -> pd.DataFrame:
    return df[df["group"] == group].copy()


def get_sample_sizes(df: pd.DataFrame) -> dict:
    return {
        "control":   len(df[df["group"] == "control"]),
        "treatment": len(df[df["group"] == "treatment"]),
        "total":     len(df),
    }


def get_date_range(df: pd.DataFrame) -> dict | None:
    if "timestamp" not in df.columns:
        return None
    return {
        "start": df["timestamp"].min(),
        "end":   df["timestamp"].max(),
        "days":  (df["timestamp"].max() - df["timestamp"].min()).days + 1,
    }


def get_device_breakdown(df: pd.DataFrame) -> pd.DataFrame | None:
    if "device" not in df.columns:
        return None
    return (
        df.groupby(["device", "group"])["converted"]
        .agg(["count", "sum", "mean"])
        .rename(columns={"count": "n", "sum": "conversions", "mean": "conv_rate"})
        .reset_index()
    )