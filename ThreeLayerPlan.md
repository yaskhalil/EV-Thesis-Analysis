# 🧠 AI / Quant (Lean) — Point72 Pitch

> **Goal:** Use a parsimonious, explainable model stack to support a **Sell** thesis with **public, free data** only.

---

## ✅ What We’re Building
- [x] **Predictive KPI** (alt data → next-qtr gross margin or deliveries)
- [x] **Factor Decomposition** (style/ beta drift)
- [x] **Regime Detection** (Expansion / Transition / Compression)
- [x] **Three plots + one-paragraph insight** per model

---

## 📦 Minimal Dataset (8 Variables Total)

| Category | Variable | Source | Notes |
|---|---|---|---|
| Fundamentals | `gross_margin_q` | SEC 10-Q | Quarterly; target for predictive model |
| Fundamentals | `deliveries_q` | Rivian IR / 10-Q | Quarterly; alternative target |
| Demand | `ev_sales_growth_m` | Argonne EV monthly sales | Convert to YoY %; aggregate to quarter |
| Cost | `lithium_price_m` | Kaggle/TradingEconomics | Spot/Index; agg to quarter (mean) |
| Cost | `electricity_price_m` | EIA API (avg retail) | Residential or commercial; agg to quarter |
| Market | `rivn_ret_d` | yfinance | Daily returns; derive volatility & factor model |
| Market | `nasdaq_ret_d` | yfinance (QQQ/NDX) | Benchmark returns |
| Market (Peer) | `tsla_ret_d` | yfinance | Industry proxy; optional factor input |

**Engineered features**
- `ev_sales_growth_q` (quarterly avg of monthly YoY)
- `lithium_price_q`, `electricity_price_q` (quarterly mean)
- `rivn_vol_q` (quarterly realized volatility from daily)
- `delivery_growth_q` (QoQ % change from `deliveries_q`)
- `gross_margin_next_q` (target shifted +1 quarter)

---

## 🥇 Model 1 — Predictive KPI (Core)

**Objective:** Forecast **`gross_margin_next_q`** (or `delivery_growth_next_q`) from demand + cost + market risk.

**Inputs (quarterly aligned):**
- `ev_sales_growth_q`
- `lithium_price_q`
- `electricity_price_q`
- `rivn_vol_q` (realized vol)
- Optional: `delivery_growth_q` (as a leading indicator for margin)

**Model:**
- [x] `ElasticNet` (primary; interpretable)  
- [ ] Try `GradientBoostingRegressor` (keep only if OOS error improves)

**Validation:**
- Rolling/expanding **time split**, not random K-fold
- Keep if **RMSE ↓ ≥ 5–10%** vs naïve last-value and **Adj.R² ↑ ≥ 0.02**

**Outputs:**
- [x] **Pred vs. Actual** `gross_margin_q` (line)
- [x] **Coefficient / Feature Importance** (bar)
- [x] 1-paragraph takeaway

**Example takeaway:**  
*“Model indicates **8–10% margin compression next quarter**, driven by higher lithium costs and flattening EV sales growth.”*

---

## 🥈 Model 2 — Factor Decomposition (Behavior)

**Objective:** Explain **RIVN** return drivers and **style drift**.

**Inputs (daily):**
- `rivn_ret_d` (dep var)
- `nasdaq_ret_d` (market)
- `tsla_ret_d` (industry peer proxy)
- Optional: Ken French factors (only if they materially improve explanatory power)

**Method:**
- Rolling 90-day OLS: `RIVN = α + β_mkt*NASDAQ + β_peer*TSLA + ε`
- Track `β_mkt`, `β_peer`, and α over time

**Outputs:**
- [x] **Rolling betas heatmap**
- [x] **Beta lines** (market & peer)
- [x] 1-paragraph takeaway

**Example takeaway:**  
*“RIVN beta to growth proxy fell from **~1.6 → ~0.9** through 2024, signaling **institutional derisking** and lower tolerance for negative margin surprise.”*

---

## 🥉 Model 3 — Regime Detection (Context)

**Objective:** Identify current **macro-fundamental regime**.

**Inputs (quarterly, normalized):**
- `gross_margin_q`
- `delivery_growth_q`
- `rivn_vol_q`
- `lithium_price_q` **or** its volatility (`Δ or σ`)

**Method:**
- Standardize → `KMeans(n=3)` (Expansion / Transition / Compression)
- 2D **PCA projection** for visualization

**Outputs:**
- [x] **Cluster map** with regimes labeled
- [x] **Timeline ribbon** of regime by quarter
- [x] 1-paragraph takeaway

**Example takeaway:**  
*“Current point clusters with historical **Compression** regime (high vol, weak margin, flat deliveries), which historically precedes **drawdowns**.”*

---

## 🧰 Implementation Checklist

- [ ] **Ingest**
  - SEC quarterly: `gross_margin_q`, `deliveries_q`
  - Argonne EV monthly → YoY → quarterly avg: `ev_sales_growth_q`
  - Lithium monthly → quarterly mean: `lithium_price_q`
  - Electricity monthly → quarterly mean: `electricity_price_q`
  - yfinance daily → `rivn_ret_d`, `nasdaq_ret_d`, `tsla_ret_d`

- [ ] **Engineer**
  - `delivery_growth_q = pct_change(deliveries_q)`
  - `rivn_vol_q` = √252 * std(daily returns within quarter)
  - Shift target: `gross_margin_next_q = gross_margin_q.shift(-1)`

- [ ] **Model 1 (ElasticNet)**
  - Time-based split; tune `α`, `l1_ratio`
  - Save: `pred_vs_actual.png`, `coef_bar.png`

- [ ] **Model 2 (Rolling OLS)**
  - 90-day window; store `β_mkt`, `β_peer`, `α`
  - Save: `beta_heatmap.png`, `beta_trend.png`

- [ ] **Model 3 (KMeans)**
  - Standardize; `k=3`; label regimes by centroid stats
  - Save: `regime_clusters.png`, `regime_timeline.png`

- [ ] **Insights**
  - 3 concise paras (one per model) for slide #9

---

## 📊 Slide Export Targets

