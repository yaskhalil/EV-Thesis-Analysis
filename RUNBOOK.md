# EV Thesis 3 Ingestion Pipeline — Runbook

## Quick Start

### 1. Run the ingestion pipeline (CLI)
```bash
cd /Users/yaseenkhalil/RivianAnalysis
python src/ingestion_standardization.py
```

**What it does:**
- Reads raw files from `data/raw/` (AFDC CSVs, EIA XLSX, NHTSA CSVs)
- Standardizes into tidy tables
- Writes 6 output CSVs to `data/processed/`

**Expected runtime:** ~30 seconds for full dataset (2021-2025, ~450k recall records)

---

### 2. Run tests
```bash
# Full test suite
pytest tests/test_ingestion_standardization.py -v

# Specific test
pytest tests/test_ingestion_standardization.py::test_run_all_with_minimal_data -v

# With coverage
pytest tests/test_ingestion_standardization.py --cov=src --cov-report=term-missing
```

**Expected:** 21 tests pass in <5 seconds.

---

## Expected Outputs

All outputs written to `data/processed/`:

### 1. `afdc_ports_per_100k_by_state_year.csv`
**Schema:** `state, date, ports_per_100k`

**Sample:**
```csv
state,date,ports_per_100k
CA,2021-10-07,125.3
CA,2022-10-07,142.8
NY,2021-10-07,87.2
```

**Equation:** `ports_per_100k = (total_ports / state_population) * 100,000`

**Typical range:** 20-200 (sparse states like WY ~20; EV hubs like CA ~180)

---

### 2. `afdc_dcfast_share_by_state_year.csv`
**Schema:** `state, date, dcfast_share`

**Sample:**
```csv
state,date,dcfast_share
CA,2021-10-07,0.18
CA,2022-10-07,0.22
```

**Equation:** `dcfast_share = dc_fast_ports / total_ports`

**Typical range:** 0.10-0.30 (road-trip corridors higher; urban L2-dominant lower)

---

### 3. `eia_res_price_residential_state_month.csv`
**Schema:** `state, month, cents_per_kWh`

**Sample:**
```csv
state,month,cents_per_kWh
CA,2024-01,27.5
NY,2024-01,21.8
TX,2024-01,13.2
```

**Typical range:** 10-35 cents/kWh (TX cheapest, HI/CA highest)

---

### 4. `eia_res_sales_per_customer_state_month.csv`
**Schema:** `state, month, MWh`

**Sample:**
```csv
state,month,MWh
CA,2024-01,12500
NY,2024-01,8900
```

**Note:** Currently reports total MWh; `MWh_per_customer` requires customer count (often absent in EIA tables).

---

### 5. `recalls_per_10k_by_make_month_12m.csv`
**Schema:** `make, month, recall_count_12m, recalls_per_10k`

**Sample:**
```csv
make,month,recall_count_12m,recalls_per_10k
RIVIAN,2023-06,8,NaN
TESLA,2023-06,24,NaN
FORD,2023-06,18,NaN
```

**Note:** `recalls_per_10k` is `NaN` (awaiting production volume data).

---

### 6. `master_panel_state_month.csv`
**Schema:** `state, month, cents_per_kWh, ports_per_100k, dcfast_share, MWh`

**Sample:**
```csv
state,month,cents_per_kWh,ports_per_100k,dcfast_share,MWh
CA,2024-01,27.5,165.2,0.22,12500
NY,2024-01,21.8,102.3,0.18,8900
```

**Purpose:** State+month panel for regression analysis (TCO vs. adoption, infrastructure vs. sales).

---

## Troubleshooting

### Issue: `EIA price: no Residential columns found`
**Cause:** Header detection failed; EIA changed table format.

**Fix:**
1. Open `data/raw/table_5_06_a.xlsx` manually.
2. Check header rows (usually rows 3-4).
3. Adjust `header=[2, 3]` in `ingest_eia_price()` if needed.
4. Verify "Residential" appears in row 3.

**Example fix:**
```python
# If headers shifted to rows 4-5
df = pd.read_excel(xlsx, sheet_name=0, header=[3, 4])
```

---

### Issue: `AFDC: could not find 'State' column`
**Cause:** AFDC renamed column (e.g., "STATE" → "State Code").

**Fix:**
1. Check actual column name: `pd.read_csv(file, nrows=1).columns`
2. Add to `_find_column()` candidates:
```python
state_col = _first_nonnull(
    [c for c in df.columns if c in ("State", "STATE", "state", "State Code")],
    "State"
)
```

---

### Issue: `AFDC: fallback to connector parsing`
**Cause:** Older snapshots lack `EV DC Fast Count` / `EV Level2 EVSE Num`.

**Expected behavior:** Module counts semicolons in `EV Connector Types`.

**Validation:** Spot-check output—aggregate port counts should be ~±10% of newer snapshots (connector counts underestimate multi-port stations).

---

### Issue: `Recalls: MAKE column not found`
**Cause:** NHTSA file uses "Manufacturer Name" instead of "MAKE".

**Fix:**
1. Check actual column: `pd.read_csv(file, nrows=1).columns`
2. Module already handles via `_first_nonnull()`:
```python
make_col = _first_nonnull(
    [c for c in df.columns if c in ("MAKE", "MANUFACTURER NAME", "MFR_NAME")],
    None,
)
```
3. If new variant appears, add to list above.

---

### Issue: `Master panel not created (missing AFDC or EIA data)`
**Cause:** One of the input files is missing or empty.

**Fix:**
1. Check logs for earlier warnings (e.g., `AFDC: no data ingested`).
2. Verify files exist in `data/raw/`:
   - `alt_fuel_stations_historical_day (Oct 7 202X).csv`
   - `table_5_06_a.xlsx`
   - `table_5_04_b.xlsx`
3. If files renamed, update paths in `main()`.

---

### Issue: `Month parsing failed` (high % NaN in `month` column)
**Cause:** EIA changed date format in column headers.

**Fix:**
1. Print column headers: `df.columns`
2. Add new format to `_safe_month_parse()`:
```python
for fmt in (
    "%Y-%m",
    "%b-%Y",
    "%Y M%m",
    "%b %d, %Y",  # Add new format here
):
```

---

### Issue: Test failures after data refresh
**Cause:** Assertions hardcoded to old data (e.g., row counts, state coverage).

**Fix:**
1. Re-run tests to see actual vs. expected.
2. If new states added (unlikely): update `DEFAULT_STATE_POP`.
3. If AFDC format changed: update column candidate lists.

---

## Development Workflow

### Adding a new data source
1. Write `ingest_X()` function (returns raw df).
2. Write `standardize_X()` function (returns tidy df with standard schema).
3. Add to `run_all()` orchestration.
4. Write tests:
   - `test_ingest_X_empty()` (missing file handling)
   - `test_ingest_X()` (valid input)
   - `test_standardize_X()` (transformations)
5. Update `TESTPLAN.md` with equations and tolerances.

---

### Updating state population
**When:** Annual (post-Census releases).

**How:**
1. Update `DEFAULT_STATE_POP` in `ingestion_standardization.py`.
2. Re-run pipeline: `python src/ingestion_standardization.py`
3. Re-run tests: `pytest tests/`
4. Commit updated population table with source citation.

---

## Code Quality

### Formatting
```bash
# Auto-format (88 chars)
black src/ tests/

# Lint
ruff check src/ tests/
```

### Type checking (optional)
```bash
mypy src/ingestion_standardization.py --strict
```

---

## Logging

All operations logged to stdout at `INFO` level:
```
2025-10-07 10:15:32 | INFO | Starting ingestion pipeline; output dir: data/processed
2025-10-07 10:15:33 | INFO | Reading AFDC file: alt_fuel_stations_historical_day (Oct 7 2024).csv
2025-10-07 10:15:35 | INFO | Ingested 68450 AFDC station records
2025-10-07 10:15:36 | INFO | AFDC standardized: 208 state-date records
...
```

**Adjust log level:**
```python
logging.basicConfig(level=logging.DEBUG)  # More verbose
logging.basicConfig(level=logging.WARNING)  # Less verbose
```

---

## Support

**Questions:** Check `tests/TESTPLAN.md` for detailed test explanations.

**Bugs:** Open issue with logs + input file snippet.

**Feature requests:** Describe use case (e.g., "Add regional aggregation for West Coast") + expected output schema.

