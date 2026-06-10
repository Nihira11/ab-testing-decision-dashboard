"""
Custom CSS for the dashboard – 'data journalism' look (FT salmon).

Design intent:
- Salmon paper background with claret as the single accent (set in .streamlit/config.toml)
- Serif display headings over sans body, like a broadsheet data section
- The signature: every number renders in monospaced tabular figures,
  set against warm paper – financial-press energy
"""

import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:wght@500;600;700&display=swap');

/* base type */
html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}

/* headings – serif display, broadsheet style */
h1, h2, h3 {
    font-family: 'IBM Plex Serif', Georgia, serif !important;
    letter-spacing: -0.01em;
}
h1 { font-weight: 700 !important; color: #33302E; }
h2 {
    font-weight: 600 !important;
    color: #33302E;
    border-bottom: 1px solid #E3CDBA;
    padding-bottom: 0.35rem;
}
h3 { font-weight: 600 !important; color: #33302E; }

/* metric cards – white panels on salmon paper */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E3CDBA;
    border-radius: 10px;
    padding: 14px 16px 10px 16px;
}
[data-testid="stMetricLabel"] {
    color: #8E8478 !important;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    font-size: 0.68rem !important;
}
[data-testid="stMetricLabel"] p,
[data-testid="stMetricLabel"] div {
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
}
[data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace !important;
    font-weight: 500;
    font-variant-numeric: tabular-nums;
    color: #33302E;
    font-size: 1.5rem !important;
    line-height: 1.25 !important;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
}
[data-testid="stMetricValue"] > div {
    font-size: inherit !important;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
}
[data-testid="stMetricDelta"] {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.85rem !important;
}

/* numbers inside tables also go mono-figured */
[data-testid="stDataFrame"] * {
    font-variant-numeric: tabular-nums;
}

/* sidebar – wheat panel with hairline edge */
[data-testid="stSidebar"] {
    border-right: 1px solid #E3CDBA;
}

/* expanders + tabs – quieter borders */
[data-testid="stExpander"] {
    border: 1px solid #E3CDBA;
    border-radius: 10px;
    background: #FFFAF4;
}
button[data-baseweb="tab"] {
    font-weight: 500;
}

/* buttons – claret outline that fills on hover */
.stButton > button, .stDownloadButton > button {
    border: 1px solid #990F3D;
    color: #990F3D;
    border-radius: 8px;
    transition: all 0.15s ease;
    background: transparent;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    background: #990F3D;
    color: #FFF1E5;
    border-color: #990F3D;
}

/* hero kicker used on the home page */
.kicker {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #990F3D;
    margin-bottom: -0.4rem;
}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)