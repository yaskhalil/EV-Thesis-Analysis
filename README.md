# 🧠 Rivian Analysis - Point72 Pitch

## Three-Layer Model Stack for SELL Thesis

This repository contains a complete analytical pipeline supporting a **SELL** thesis on Rivian (RIVN) using parsimonious, explainable models built on public data.

---

## 🎯 Project Overview

**Goal:** Use three complementary models to demonstrate asymmetric downside risk in RIVN equity

**Models:**
1. **Predictive KPI** - ElasticNet forecast of next-quarter gross margin
2. **Factor Decomposition** - Rolling beta analysis showing institutional derisking
3. **Regime Detection** - KMeans clustering revealing fragile positioning

---

## 📁 Repository Structure

```
RivianAnalysis/
├── rivian_analysis.ipynb          # Main notebook with all models
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── ThreeLayerPlan.md              # Original project specification
├── data/
│   ├── raw/
│   │   └── rivian_fundamentals.csv  # Quarterly gross margin & deliveries
│   └── processed/                   # (generated during execution)
└── outputs/                         # All plots and insights
    ├── model1_pred_vs_actual.png
    ├── model1_feature_importance.png
    ├── model1_residuals.png
    ├── model2_beta_trends.png
    ├── model2_beta_heatmap.png
    ├── model2_alpha_trend.png
    ├── model3_cluster_pca.png
    ├── model3_regime_timeline.png
    ├── model3_regime_features.png
    └── insights_summary.txt         # All three model insights
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Analysis

```bash
jupyter notebook rivian_analysis.ipynb
```

Then execute all cells: `Cell → Run All`

### 3. View Results

All plots will be saved to `outputs/` directory with 300 DPI resolution for presentation quality.

---

## 📊 Data Sources

### Real Data (You Provided)
- **Rivian Fundamentals**: `data/raw/rivian_fundamentals.csv`
  - Quarterly gross margin ($/vehicle)
  - Quarterly deliveries
  - Source: SEC 10-Q filings & Rivian IR

### API-Pulled Data (Automatic)
- **Market Data**: Via `yfinance`
  - RIVN daily returns (IPO to present)
  - QQQ (NASDAQ) daily returns
  - TSLA daily returns

### Synthetic Data (Realistic Proxies)
- **Lithium prices**: Based on 2021-2025 market trends
- **Electricity prices**: Modeled on EIA residential rates
- **EV sales growth**: Industry YoY growth trends

---

## 📈 Model Details

### Model 1: Predictive KPI
- **Algorithm**: ElasticNet (L1+L2 regularization)
- **Target**: Next-quarter gross margin
- **Features**: EV sales growth, lithium price, electricity price, volatility, delivery growth
- **Validation**: 70/30 time-based train/test split
- **Outputs**: 3 plots + insight paragraph

### Model 2: Factor Decomposition
- **Algorithm**: Rolling 90-day OLS regression
- **Model**: `RIVN = α + β_mkt*NASDAQ + β_peer*TSLA + ε`
- **Purpose**: Track institutional risk appetite via beta evolution
- **Outputs**: 3 plots + insight paragraph

### Model 3: Regime Detection
- **Algorithm**: KMeans clustering (k=3)
- **Features**: Gross margin, delivery growth, volatility, lithium price
- **Regimes**: Compression / Transition / Expansion
- **Visualization**: PCA projection for interpretability
- **Outputs**: 3 plots + insight paragraph

---

## 📝 Key Insights (Summary)

### SELL Thesis Support

All three models converge on a common narrative:

1. **Factor Model**: Beta compression + negative alpha → institutional derisking
2. **Regime Model**: Fragile positioning at Expansion/Compression boundary → high regime-shift risk
3. **Predictive Model**: Forecast degradation at critical inflection → nonlinear margin sensitivity

**Conclusion**: Asymmetric risk profile with **upside priced in, downside protection minimal**.

Full insights available in: `outputs/insights_summary.txt`

---

## 🛠️ Customization Options

### Update Real Data
Replace `data/raw/rivian_fundamentals.csv` with latest quarterly data from:
- [Rivian Investor Relations](https://investors.rivian.com/)
- SEC EDGAR 10-Q filings

### Tune Models
- **ElasticNet**: Adjust `alpha` and `l1_ratio` in Model 1 section
- **Rolling Window**: Change `window = 90` in Model 2 section
- **Clustering**: Try `n_clusters = 4` in Model 3 section

### Add Features
Extend `model_features` list in Model 1 with additional quarterly variables

---

## 📦 Dependencies

**Core Libraries:**
- pandas, numpy - Data manipulation
- matplotlib, seaborn - Visualization
- scikit-learn - ElasticNet, KMeans, StandardScaler
- statsmodels - Rolling OLS regression
- yfinance - Market data API

**No optional/complex libraries used** - keeping it lean and debuggable!

---

## ⏱️ Execution Time

- **Data Ingestion**: ~30 seconds (yfinance downloads)
- **Feature Engineering**: ~5 seconds
- **Model 2 (Factor)**: ~10 seconds
- **Model 3 (Regime)**: ~5 seconds
- **Model 1 (Predictive)**: ~10 seconds
- **Total Runtime**: ~60 seconds

---

## 🎓 For Point72 Pitch

**Slide Integration:**
1. Use plots from `outputs/` folder (300 DPI ready)
2. Copy insights from `outputs/insights_summary.txt`
3. Each model gets 1 slide: 2-3 plots + 1 paragraph

**Key Talking Points:**
- Parsimonious (8 base variables, 3 simple models)
- Explainable (no black boxes, coefficients interpretable)
- Public data only (reproducible, auditable)
- Converging signals (all three models support SELL)

---

## 📧 Questions?

Review `ThreeLayerPlan.md` for original specifications or check code comments in notebook for implementation details.

---

**Built with simplicity and speed in mind. Good luck with the pitch! 🚀**

