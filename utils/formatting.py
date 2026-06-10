"""
Formatting helpers for Streamlit pages.
All functions return strings ready for st.metric(), st.markdown(), or dataframe display.
"""


# number formatters

def fmt_pct(value: float, decimals: int = 2, sign: bool = False) -> str:
    multiplied = value * 100
    if sign:
        return f"{multiplied:+.{decimals}f}%"
    return f"{multiplied:.{decimals}f}%"


def fmt_pct_raw(value: float, decimals: int = 2, sign: bool = False) -> str:
    if sign:
        return f"{value:+.{decimals}f}%"
    return f"{value:.{decimals}f}%"


def fmt_currency(value: float, currency: str = "USD", decimals: int = 0) -> str:
    symbols = {"USD": "$", "GBP": "£", "EUR": "€", "AUD": "A$"}
    symbol = symbols.get(currency, "$")
    if decimals == 0:
        return f"{symbol}{value:,.0f}"
    return f"{symbol}{value:,.{decimals}f}"


def fmt_currency_signed(value: float, currency: str = "USD", decimals: int = 0) -> str:
    symbols = {"USD": "$", "GBP": "£", "EUR": "€", "AUD": "A$"}
    symbol = symbols.get(currency, "$")
    sign = "+" if value >= 0 else "-"
    if decimals == 0:
        return f"{sign}{symbol}{abs(value):,.0f}"
    return f"{sign}{symbol}{abs(value):,.{decimals}f}"


def fmt_number(value: float, decimals: int = 0) -> str:
    return f"{value:,.{decimals}f}"


def fmt_pvalue(p: float) -> str:
    if p < 0.001:
        return "p < 0.001"
    return f"p = {p:.4f}"


def fmt_stat(value: float, decimals: int = 4) -> str:
    """For z-stats, t-stats, chi2 – always show sign."""
    return f"{value:+.{decimals}f}"


def fmt_ci(low: float, high: float, as_pct: bool = True, decimals: int = 2) -> str:
    if as_pct:
        return f"[{low*100:.{decimals}f}%, {high*100:.{decimals}f}%]"
    return f"[{low:.{decimals}f}, {high:.{decimals}f}]"


# significance labels

def significance_label(p_value: float, alpha: float = 0.05) -> str:
    if p_value < 0.001:
        return "Highly significant (p < 0.001)"
    elif p_value < alpha:
        return f"Significant ({fmt_pvalue(p_value)})"
    else:
        return f"Not significant ({fmt_pvalue(p_value)})"


def significance_badge(significant: bool) -> str:
    if significant:
        return "**[SIGNIFICANT]**"
    return "**[NOT SIGNIFICANT]**"


def confidence_badge(confidence: str) -> str:
    return f"**[{confidence.upper()}]**"


def recommendation_badge(recommendation: str) -> str:
    return f"**[{recommendation.upper()}]**"


def risk_badge(risk: str) -> str:
    return f"**[{risk.upper()} RISK]**"


# delta helpers (for st.metric delta parameter)

def delta_pct(value: float, decimals: int = 2) -> str:
    return fmt_pct(value, decimals=decimals, sign=True)


def delta_pct_raw(value: float, decimals: int = 2) -> str:
    return fmt_pct_raw(value, decimals=decimals, sign=True)


def delta_currency(value: float, currency: str = "USD") -> str:
    return fmt_currency_signed(value, currency=currency)


# colour helpers (Plotly)

COLOURS = {
    "control":   "#0F5499",   # oxford blue – variant A
    "treatment": "#990F3D",   # claret – variant B
    "prior":     "#B3A893",   # warm grey
    "positive":  "#0D7680",   # FT teal
    "negative":  "#C7331D",   # vermilion
    "neutral":   "#8E8478",   # warm grey
    "highlight": "#262A33",  # slate annotation
}


def group_colour(group: str) -> str:
    return COLOURS.get(group.lower(), COLOURS["neutral"])


def lift_colour(value: float) -> str:
    return COLOURS["positive"] if value >= 0 else COLOURS["negative"]