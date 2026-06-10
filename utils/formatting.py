"""
Formatting helpers for Streamlit pages.
All functions return strings ready for st.metric(), st.markdown(), or dataframe display.
"""


# number formatters

def fmt_pct(value: float, decimals: int = 2, sign: bool = False) -> str:
    """
    Format a float as a percentage string.
    fmt_pct(0.0501)        → '5.01%'
    fmt_pct(0.0074, sign=True) → '+0.74%'
    """
    multiplied = value * 100
    if sign:
        return f"{multiplied:+.{decimals}f}%"
    return f"{multiplied:.{decimals}f}%"


def fmt_pct_raw(value: float, decimals: int = 2, sign: bool = False) -> str:
    """
    Format a value that is already in percentage form (e.g. 14.77, not 0.1477).
    fmt_pct_raw(14.77)          → '14.77%'
    fmt_pct_raw(14.77, sign=True) → '+14.77%'
    """
    if sign:
        return f"{value:+.{decimals}f}%"
    return f"{value:.{decimals}f}%"


def fmt_currency(value: float, currency: str = "USD", decimals: int = 0) -> str:
    """
    Format a float as a currency string.
    fmt_currency(303862)       → '$303,862'
    fmt_currency(832.50, decimals=2) → '$833'
    """
    symbols = {"USD": "$", "GBP": "£", "EUR": "€", "AUD": "A$"}
    symbol = symbols.get(currency, "$")
    if decimals == 0:
        return f"{symbol}{value:,.0f}"
    return f"{symbol}{value:,.{decimals}f}"


def fmt_currency_signed(value: float, currency: str = "USD", decimals: int = 0) -> str:
    """
    fmt_currency_signed(303862)  → '+$303,862'
    fmt_currency_signed(-5000)   → '-$5,000'
    """
    symbols = {"USD": "$", "GBP": "£", "EUR": "€", "AUD": "A$"}
    symbol = symbols.get(currency, "$")
    sign = "+" if value >= 0 else "-"
    if decimals == 0:
        return f"{sign}{symbol}{abs(value):,.0f}"
    return f"{sign}{symbol}{abs(value):,.{decimals}f}"


def fmt_number(value: float, decimals: int = 0) -> str:
    """
    fmt_number(10000)    → '10,000'
    fmt_number(0.9893, decimals=4) → '0.9890'
    """
    return f"{value:,.{decimals}f}"


def fmt_pvalue(p: float) -> str:
    """
    Human-readable p-value formatting.
    fmt_pvalue(0.0204)  → 'p = 0.0204'
    fmt_pvalue(0.0001)  → 'p < 0.001'
    fmt_pvalue(0.9500)  → 'p = 0.9500'
    """
    if p < 0.001:
        return "p < 0.001"
    return f"p = {p:.4f}"


def fmt_stat(value: float, decimals: int = 4) -> str:
    """For z-stats, t-stats, chi2 – always show sign."""
    return f"{value:+.{decimals}f}"


def fmt_ci(low: float, high: float, as_pct: bool = True, decimals: int = 2) -> str:
    """
    Format a confidence/credible interval.
    fmt_ci(0.0460, 0.0546, as_pct=True)  → '[4.60%, 5.46%]'
    fmt_ci(2.10, 3.20, as_pct=False)     → '[2.10, 3.20]'
    """
    if as_pct:
        return f"[{low*100:.{decimals}f}%, {high*100:.{decimals}f}%]"
    return f"[{low:.{decimals}f}, {high:.{decimals}f}]"


# significance labels

def significance_label(p_value: float, alpha: float = 0.05) -> str:
    """Returns a short significance label for display."""
    if p_value < 0.001:
        return "Highly significant (p < 0.001)"
    elif p_value < alpha:
        return f"Significant ({fmt_pvalue(p_value)})"
    else:
        return f"Not significant ({fmt_pvalue(p_value)})"


def significance_badge(significant: bool) -> str:
    """Returns a markdown badge string for st.markdown()."""
    if significant:
        return "**[SIGNIFICANT]**"
    return "**[NOT SIGNIFICANT]**"


def confidence_badge(confidence: str) -> str:
    """Returns a markdown badge for decision confidence."""
    return f"**[{confidence.upper()}]**"


def recommendation_badge(recommendation: str) -> str:
    """Returns a styled markdown string for the final decision."""
    return f"**[{recommendation.upper()}]**"


def risk_badge(risk: str) -> str:
    return f"**[{risk.upper()} RISK]**"


# delta helpers (for st.metric delta parameter)

def delta_pct(value: float, decimals: int = 2) -> str:
    """
    Returns a signed % string for use as st.metric delta.
    delta_pct(0.0074) → '+0.74%'
    """
    return fmt_pct(value, decimals=decimals, sign=True)


def delta_pct_raw(value: float, decimals: int = 2) -> str:
    """For values already in % form. delta_pct_raw(14.77) → '+14.77%'"""
    return fmt_pct_raw(value, decimals=decimals, sign=True)


def delta_currency(value: float, currency: str = "USD") -> str:
    """Returns a signed currency string for st.metric delta."""
    return fmt_currency_signed(value, currency=currency)


# colour helpers (Plotly)

COLOURS = {
    "control":   "#4C72B0",   # muted blue
    "treatment": "#DD8452",   # muted orange
    "prior":     "#CCCCCC",   # light grey
    "positive":  "#2CA02C",   # green
    "negative":  "#D62728",   # red
    "neutral":   "#7F7F7F",   # grey
    "highlight": "#9467BD",   # purple accent
}


def group_colour(group: str) -> str:
    """Returns the Plotly colour for a given group label."""
    return COLOURS.get(group.lower(), COLOURS["neutral"])


def lift_colour(value: float) -> str:
    """Green if positive lift, red if negative."""
    return COLOURS["positive"] if value >= 0 else COLOURS["negative"]


# quick test

if __name__ == "__main__":
    print("=== Percentage formatters ===")
    print(fmt_pct(0.0501))
    print(fmt_pct(0.0074, sign=True))
    print(fmt_pct_raw(14.77, sign=True))

    print("\n=== Currency formatters ===")
    print(fmt_currency(303862))
    print(fmt_currency(832.50, decimals=2))
    print(fmt_currency_signed(303862))
    print(fmt_currency_signed(-5000))

    print("\n=== Stat formatters ===")
    print(fmt_pvalue(0.0204))
    print(fmt_pvalue(0.0001))
    print(fmt_stat(2.3192))
    print(fmt_ci(0.0460, 0.0546, as_pct=True))
    print(fmt_ci(2.10, 3.20, as_pct=False))

    print("\n=== Badges ===")
    print(significance_badge(True))
    print(significance_badge(False))
    print(confidence_badge("HIGH"))
    print(recommendation_badge("SHIP"))
    print(recommendation_badge("DO NOT SHIP"))
    print(recommendation_badge("CONTINUE TESTING"))
    print(risk_badge("LOW"))

    print("\n=== Delta helpers ===")
    print(delta_pct(0.0074))
    print(delta_pct_raw(14.77))
    print(delta_currency(303862))
    print(delta_currency(-5000))

    print("\n=== Colours ===")
    print(group_colour("control"))
    print(group_colour("treatment"))
    print(lift_colour(0.0074))
    print(lift_colour(-0.002))