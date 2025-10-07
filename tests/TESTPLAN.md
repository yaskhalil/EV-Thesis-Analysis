# Test Plan: EV Thesis 3 Ingestion & Standardization

## Overview
Tests validate data ingestion from three public sources (AFDC, EIA, NHTSA) and standardization into metrics supporting the EV investment thesis: infrastructure tailwind, TCO economics, and quality risk.

---

## Helper Function Tests

### `test_safe_month_parse`
**Validates:** Robust month parsing across varying date formats.

**Why it matters:** EIA tables use inconsistent date formats ("Jan-2024", "2024-01", "2024 M01"). Parser failures corrupt time-series joins in master panel.

**Expected:** All format variants → `pd.Timestamp('2024-01-01')`

**Tolerance:** None; must be exact first-of-month.

---

### `test_parse_nhtsa_date`
**Validates:** NHTSA ID extraction to date (e.g., "20E003" → 2020-01-01).

**Why it matters:** Recall files lack explicit dates; NHTSA ID is only temporal signal for trending analysis.

**Expected:** "20E003" → 2020, "23V456" → 2023

**Tolerance:** Year-level precision sufficient for 12-month rolling metrics.

---

## AFDC (Infrastructure) Tests

### `test_ingest_afdc_historical`
**Validates:** Multi-file CSV stacking with snapshot date inference from filenames.

**Why it matters:** AFDC publishes quarterly snapshots; miss dates → lose temporal ordering.

**Expected:** 
- Filename `alt_fuel_stations_historical_day (Oct 7 2021).csv` → `snapshot_date = 2021-10-07`
- Combined df has `snapshot_date` column

---

### `test_ingest_afdc_historical_fallback_connectors`
**Validates:** Fallback logic when explicit port count columns absent.

**Why it matters:** Older AFDC snapshots lack `EV DC Fast Count` / `EV Level2 EVSE Num`; must parse semicolon-separated `EV Connector Types`.

**Expected:** Station with `"J1772; CCS; CHAdeMO"` → 3 ports (fallback count)

**Tolerance:** ±1 port acceptable for aggregate state metrics.

---

### `test_standardize_afdc`
**Validates:** State-level aggregation with population normalization.

**Equation:**
```
ports_per_100k = (total_ports / state_population) * 100,000
dcfast_share = dc_fast_ports / total_ports
```

**Why it matters:** Raw port counts favor large states (CA, TX); per-capita normalization reveals infrastructure gaps. DC fast share indicates road-trip readiness.

**Expected output (sample):**
```csv
state,date,ports_per_100k
CA,2021-10-07,125.3
NY,2021-10-07,87.2
```

**Tolerance:** ±2% (population estimates vary by source).

---

### `test_standardize_afdc_invalid_states`
**Validates:** Filters non-2-letter state codes (e.g., "XX", foreign codes).

**Why it matters:** AFDC includes Canada, Mexico stations; non-US codes break population joins.

**Expected:** Input with "CA" and "XX" → only "CA" in output.

---

## EIA (TCO Economics) Tests

### `test_ingest_eia_price`
**Validates:** Wide-to-tidy transformation for residential electricity prices.

**Why it matters:** EIA tables have months as columns; need tidy format for time-series merge with AFDC.

**Expected output:**
```csv
state,month,cents_per_kWh
CA,2024-01,19.5
NY,2024-01,21.3
```

**Tolerance:** ±0.1 cents (rounding in EIA source).

---

### `test_ingest_eia_sales`
**Validates:** Wide-to-tidy transformation for residential sales (MWh).

**Why it matters:** Sales per customer proxies household energy usage → EV adoption sensitivity.

**Expected output:**
```csv
state,month,MWh
CA,2024-01,1000
NY,2024-01,800
```

**Tolerance:** ±1% (aggregation rounding).

---

### `test_standardize_eia`
**Validates:** Sorting and schema consistency post-ingestion.

**Why it matters:** Master panel join requires monotonic state+month ordering.

**Expected:** Sorted by `[state, month]` ascending.

---

## NHTSA (Quality Risk) Tests

### `test_ingest_recalls`
**Validates:** Multi-file stacking of recall CSVs.

**Why it matters:** NHTSA publishes annual bulk files; need combined view across 2020-2025.

**Expected:** Concatenated df with all recall records.

---

### `test_standardize_recalls`
**Validates:** Make-level aggregation with 12-month rolling counts.

**Equation:**
```
recall_count_12m = rolling_sum(recall_count, window=12)
recalls_per_10k = recall_count_12m / (production_volume / 10,000)  [future]
```

**Why it matters:** Spike in Rivian recalls (2023-2024) flags quality risk vs. Tesla/Ford baseline.

**Expected output:**
```csv
make,month,recall_count_12m,recalls_per_10k
RIVIAN,2023-01,3,NaN
TESLA,2023-01,12,NaN
```

**Tolerance:** ±1 recall (exact counts critical for small batches).

**Note:** `recalls_per_10k` requires external production volume data (not yet integrated).

---

### `test_standardize_recalls_filter_makes`
**Validates:** Make filtering (e.g., only ["RIVIAN", "TESLA"]).

**Why it matters:** Deck focuses on EV OEMs; excluding ICE recalls reduces noise.

**Expected:** Only specified makes in output.

---

## Integration Tests

### `test_run_all_with_minimal_data`
**Validates:** End-to-end pipeline from raw files to CSVs.

**Why it matters:** Regression check; ensures schema changes don't break orchestration.

**Expected outputs:**
1. `afdc_ports_per_100k_by_state_year.csv`
2. `afdc_dcfast_share_by_state_year.csv`
3. `eia_res_price_residential_state_month.csv`
4. `eia_res_sales_per_customer_state_month.csv`
5. `recalls_per_10k_by_make_month_12m.csv`
6. `master_panel_state_month.csv` (left join of AFDC + EIA on state+month)

**Tolerance:** All files must exist and contain >0 rows.

---

### `test_run_all_missing_files`
**Validates:** Graceful handling of missing input files (log warnings, no crash).

**Why it matters:** Production runs may have incomplete data drops; must degrade gracefully.

**Expected:** Warnings logged; empty CSVs or files omitted.

---

### `test_state_population_coverage`
**Validates:** `DEFAULT_STATE_POP` includes all 50 states + DC + PR.

**Why it matters:** Missing states → `NaN` in `ports_per_100k` → broken charts.

**Expected:** 52 state codes covered.

---

### `test_state_name_mapping_coverage`
**Validates:** `STATE_NAME_TO_ABBR` maps EIA full names (e.g., "California") to codes.

**Why it matters:** EIA uses full names; AFDC uses codes; mapping failure breaks master panel join.

**Expected:** All 52 states mappable.

---

## Extension Guide

### Add production volume for `recalls_per_10k`
1. Source production data (e.g., WardsAuto, NHTSA VIN decoder).
2. Add `production_volume` column in `standardize_recalls()`.
3. Compute: `recalls_per_10k = recall_count_12m / (production_volume / 10_000)`
4. Update test to assert `recalls_per_10k.notna()`.

**Equation (denominator):**
```python
# Sum last 12 months of production for each make
production_12m = production_df.groupby("make")["monthly_volume"].rolling(12).sum()
recalls_per_10k = (recall_count_12m / production_12m) * 10_000
```

---

### Add EV parc (vehicles in operation)
1. Ingest Experian/R.L. Polk registration data or IHS Markit parc estimates.
2. Merge with master panel on `state + month`.
3. Compute: `ports_per_10k_evs = (ports / ev_parc) * 10_000`
4. Add test: `test_standardize_afdc_with_parc()`.

**Why it matters:** Population denominator is crude; EV parc reveals true charger adequacy.

---

### Add regional aggregation
1. Define census regions (e.g., West = [CA, OR, WA, ...]).
2. Aggregate state-level metrics: `grp = df.groupby("region").sum()`
3. Add test: `test_afdc_regional_aggregation()`.

**Why it matters:** Regional patterns (West Coast adoption vs. Midwest lag) inform deployment strategy.

---

## Test Maintenance

**Run on data refresh:** Re-run full suite when AFDC/EIA/NHTSA publish new files.

**Update tolerances:** If population source changes (e.g., 2024 Census), update `DEFAULT_STATE_POP` and re-baseline test assertions.

**Add edge cases:** If new AFDC column variants appear (e.g., "EVSE_DC_Fast"), add to `_find_column()` candidates and test fallback.

