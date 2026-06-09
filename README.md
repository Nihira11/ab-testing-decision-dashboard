# A/B Testing + Decision Analysis Dashboard

An end-to-end A/B testing analysis engine with both frequentist and Bayesian statistical frameworks, wrapped in an interactive Streamlit dashboard for business decision-making.

## Overview

Most A/B testing tools stop at p-values. This project goes further — translating statistical results into **business decisions** with revenue impact estimates, risk-adjusted recommendations, and Bayesian probability of winning.

Built as a portfolio project targeting fintech and quant-adjacent roles.

## Features

- **Experiment Simulator** — generate synthetic A/B test data with configurable parameters
- **Frequentist Testing** — z-tests, t-tests, chi-square, MDE, power analysis, confidence intervals
- **Bayesian Analysis** — Beta-Binomial model, prior/posterior visualisation, probability of being best, expected loss
- **Decision Engine** — expected revenue impact, risk-adjusted launch recommendation, scenario analysis
- **Streamlit Dashboard** — interactive UI with Plotly charts, uploadable real data, exportable report

## Tech Stack

| Layer | Tools |
|---|---|
| Language | Python 3.11+ |
| Statistics | scipy, statsmodels |
| Bayesian | PyMC / scipy.stats |
| Visualisation | Plotly, matplotlib |
| Dashboard | Streamlit |
| Data | pandas, numpy |

## Project Structure

```
ab-testing-decision-dashboard/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── data/
│   ├── simulated_ab_test.csv
│   └── experiment_config.json
│
├── src/
│   ├── __init__.py
│   ├── experiment_simulator.py
│   ├── stats_engine.py
│   ├── bayesian_engine.py
│   ├── decision_engine.py
│   └── report_generator.py
│
├── pages/
│   ├── 1_Experiment_Overview.py
│   ├── 2_Frequentist_Analysis.py
│   ├── 3_Bayesian_Analysis.py
│   ├── 4_Decision_Centre.py
│   └── 5_Report_Summary.py
│
├── notebooks/
│   └── ab_test_exploration.ipynb
│
├── utils/
│   ├── __init__.py
│   ├── data_loader.py
│   ├── plotting.py
│   └── formatting.py
│
├── screenshots/
│
└── reports/
    └── experiment_summary_report.pdf
```

## Getting Started

```bash
git clone https://github.com/yourusername/ab-testing-decision-dashboard.git
cd ab-testing-decision-dashboard
pip install -r requirements.txt

# run the dashboard
streamlit run app.py
```

## Demo Scenario

Control group: 5.0% conversion rate (10,000 users)  
Treatment group: 5.8% conversion rate (10,000 users)  
Business question: *Is the lift real, and is it worth launching?*

## Status

🚧 In progress
