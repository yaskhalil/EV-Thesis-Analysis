# EV Thesis 3: Data Ingestion & Standardization Pipeline

Production-grade data pipeline for electric vehicle market analysis, ingesting and standardizing data from three key public sources to support investment thesis on infrastructure tailwinds, TCO economics, and quality risk.

## 🎯 Overview

This pipeline processes:
1. **AFDC** (Alternative Fuels Data Center) - EV charging infrastructure historical snapshots
2. **EIA** (Energy Information Administration) - Residential electricity prices and sales
3. **NHTSA** (National Highway Traffic Safety Administration) - Vehicle recall data

**Output:** Standardized, tidy CSV files ready for analysis and visualization.

## 🚀 Quick Start

```bash
# Setup environment
conda env create -f environment.yml
conda activate rivian_analysis

# Run pipeline
python src/ingestion_standardization.py

# Run tests
pytest tests/test_ingestion_standardization.py -v
```

## 📊 Data Sources & Outputs

### Input Files (place in `data/raw/`)
- `alt_fuel_stations_historical_day (Oct 7 YYYY).csv` - AFDC quarterly snapshots
- `table_5_06_a.xlsx` - EIA residential electricity prices
- `table_5_04_b.xlsx` - EIA residential sales/customers
- `RCL_FROM_YYYY_YYYY.csv` - NHTSA recall bulk files
- `Safercar_data.csv` - Optional NHTSA vehicle metadata

### Output Files (`data/processed/`)
| File | Schema | Purpose |
|------|--------|---------|
| `afdc_ports_per_100k_by_state_year.csv` | state, date, ports_per_100k | Infrastructure per capita |
| `afdc_dcfast_share_by_state_year.csv` | state, date, dcfast_share | Road-trip readiness metric |
| `eia_res_price_residential_state_month.csv` | state, month, cents_per_kWh | Electricity TCO component |
| `eia_res_sales_per_customer_state_month.csv` | state, month, MWh | Household energy usage |
| `recalls_per_10k_by_make_month_12m.csv` | make, month, recall_count_12m | Quality risk (rolling 12m) |
| `master_panel_state_month.csv` | state, month, [all metrics] | State-month panel for regression |

## 📈 Key Metrics

### Infrastructure Tailwind
```python
ports_per_100k = (total_charging_ports / state_population) * 100,000
dcfast_share = dc_fast_ports / total_ports
```

### TCO Economics
- Residential electricity price (cents/kWh) by state-month
- Sales per customer (MWh) as proxy for household energy usage

### Quality Risk
```python
recall_count_12m = rolling_sum(recalls, window=12)
# Future: recalls_per_10k = recall_count_12m / (production_volume / 10,000)
```

## 🧪 Testing

**21 tests, 100% passing**

```bash
# Full suite
pytest tests/test_ingestion_standardization.py -v

# With coverage
pytest tests/test_ingestion_standardization.py --cov=src --cov-report=term-missing

# Specific test
pytest tests/test_ingestion_standardization.py::test_standardize_afdc -v
```

See [`tests/TESTPLAN.md`](tests/TESTPLAN.md) for detailed test documentation.

## 📖 Documentation

- **[RUNBOOK.md](RUNBOOK.md)** - Operations guide: how to run, troubleshoot, and extend
- **[tests/TESTPLAN.md](tests/TESTPLAN.md)** - Test strategy, equations, tolerances, and extension guide

## 🏗️ Architecture

### Design Principles
- **Pandas-first:** Pure pandas operations, no external network calls
- **Robust parsing:** Handles column variations, date format inconsistencies, missing data
- **Type-safe:** Type hints throughout, Black/Ruff compliant
- **Testable:** Small, pure functions with clear contracts
- **Observable:** INFO-level logging for production traceability

### Module Structure
```
src/ingestion_standardization.py
├── ingest_afdc_historical()      # Stack CSV snapshots
├── standardize_afdc()             # Compute per-capita metrics
├── ingest_eia_price()             # Parse wide Excel → tidy
├── ingest_eia_sales()             # Parse wide Excel → tidy
├── standardize_eia()              # Sort and validate
├── ingest_recalls()               # Stack NHTSA CSVs
├── standardize_recalls()          # Rolling 12m aggregation
└── run_all()                      # Orchestrate full pipeline
```

## 🔧 Edge Cases Handled

✅ **AFDC:** Missing port count columns → fallback to connector parsing  
✅ **AFDC:** Invalid state codes (Canada, Mexico) → filtered out  
✅ **EIA:** Multi-level Excel headers → robust parsing  
✅ **EIA:** Varying date formats → 10+ format patterns supported  
✅ **NHTSA:** Column name variants ("MAKE" vs "Manufacturer Name")  
✅ **NHTSA:** Missing dates → extract from NHTSA ID  

## 🚧 Future Enhancements

**Production Volume Integration** (for `recalls_per_10k`)
- Source: WardsAuto, NHTSA VIN decoder, or IHS Markit
- Add production volume column to `standardize_recalls()`
- Compute: `recalls_per_10k = (recall_count_12m / production_12m) * 10,000`

**EV Parc Data** (for true charger adequacy)
- Source: Experian registration data or IHS Markit
- Compute: `ports_per_10k_evs = (ports / ev_parc) * 10,000`
- Reveals true infrastructure gaps vs. crude population denominator

**Regional Aggregation**
- Define census regions (West, Midwest, Northeast, South)
- Aggregate state metrics for regional trend analysis

See [`tests/TESTPLAN.md`](tests/TESTPLAN.md) for detailed extension guide.

## 🛠️ Development

### Code Quality
```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check (optional)
mypy src/ingestion_standardization.py --strict
```

### Adding a New Data Source
1. Write `ingest_X()` function (returns raw DataFrame)
2. Write `standardize_X()` function (returns tidy DataFrame)
3. Add to `run_all()` orchestration
4. Write tests (empty, valid input, edge cases)
5. Document in TESTPLAN.md

## 📊 Sample Output

### AFDC (Infrastructure)
```csv
state,date,ports_per_100k
CA,2021-10-07,125.3
CA,2022-10-07,142.8
NY,2021-10-07,87.2
```

### Master Panel (State-Month)
```csv
state,month,cents_per_kWh,ports_per_100k,dcfast_share,MWh
CA,2024-01,27.5,165.2,0.22,12500
NY,2024-01,21.8,102.3,0.18,8900
```

## 🤝 Contributing

This is a focused research pipeline. For bugs or feature requests:
1. Open an issue with logs + data snippet
2. Describe expected vs. actual behavior
3. Include environment details (`python --version`, `pandas.__version__`)

## 📄 License

Internal research use. Contact author for external use permissions.

## 👤 Author

Yaseen Khalil

---

**Status:** ✅ Production-ready | **Tests:** 21/21 passing | **Coverage:** Core functions 100%

