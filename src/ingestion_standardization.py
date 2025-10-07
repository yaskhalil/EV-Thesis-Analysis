"""
Data Ingestion & Standardization Module (EV Thesis 3)
=====================================================
Focused on THREE public sources:
  1) AFDC historical station snapshots (CSV)  -> infrastructure tailwind
  2) EIA residential electricity prices/sales (XLSX) -> TCO tailwind
  3) NHTSA recall bulk files + Safercar metadata (CSV) -> quality risk

Output CSVs (to specified output dir):
  - afdc_ports_per_100k_by_state_year.csv
  - afdc_dcfast_share_by_state_year.csv
  - eia_res_price_residential_state_month.csv
  - eia_res_sales_per_customer_state_month.csv
  - recalls_per_10k_by_make_month_12m.csv
  - master_panel_state_month.csv   (joins AFDC + EIA on state+time)

Design notes
------------
* Pure pandas; no external web calls. Robust to common header/format quirks.
* Clear, typed functions; standardized tidy schemas.
* Logging for traceability; safe defaults.
* Black/Ruff compliant (88 chars).

Usage
-----
from src.ingestion_standardization import run_all, Paths
run_all(paths, out_dir)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("ev_ingest")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STATE_ABBR = {
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
    "DC",
    "PR",
}

STATE_NAME_TO_ABBR = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
    "District of Columbia": "DC",
    "Puerto Rico": "PR",
}

# Static state population table (2023 Census ACS estimates)
DEFAULT_STATE_POP = pd.DataFrame(
    {
        "state": [
            "AL",
            "AK",
            "AZ",
            "AR",
            "CA",
            "CO",
            "CT",
            "DE",
            "FL",
            "GA",
            "HI",
            "ID",
            "IL",
            "IN",
            "IA",
            "KS",
            "KY",
            "LA",
            "ME",
            "MD",
            "MA",
            "MI",
            "MN",
            "MS",
            "MO",
            "MT",
            "NE",
            "NV",
            "NH",
            "NJ",
            "NM",
            "NY",
            "NC",
            "ND",
            "OH",
            "OK",
            "OR",
            "PA",
            "RI",
            "SC",
            "SD",
            "TN",
            "TX",
            "UT",
            "VT",
            "VA",
            "WA",
            "WV",
            "WI",
            "WY",
            "DC",
            "PR",
        ],
        "population": [
            5074296,
            733406,
            7359197,
            3045637,
            38965193,
            5893634,
            3626205,
            1035009,
            22391017,
            11029004,
            1440195,
            1964727,
            12582032,
            6882403,
            3200517,
            2937150,
            4512310,
            4600186,
            1385340,
            6185277,
            7055253,
            10056478,
            5717184,
            2940054,
            6169038,
            1122867,
            1960790,
            3177772,
            1379617,
            9387343,
            2120220,
            19491339,
            10600823,
            812615,
            11712533,
            4019800,
            4237256,
            12821920,
            1093994,
            5328210,
            919324,
            7067904,
            30390355,
            3430800,
            647464,
            8734853,
            7797095,
            1755715,
            5892539,
            581381,
            671803,
            3263587,
        ],
    }
)


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
def _safe_month_parse(s: str) -> pd.Timestamp | None:
    """Parse month strings robustly to first day of month.

    Handles formats: 'Jan-2024', '2024-01', '1/2024', '2024 M01', etc.
    """
    if pd.isna(s):
        return None
    s = str(s).strip()

    # Try common date formats
    for fmt in (
        "%Y-%m",
        "%b-%Y",
        "%b %Y",
        "%Y %m",
        "%m/%Y",
        "%Y%m",
        "%Y %b",
        "%b-%y",
        "%Y-M%m",
        "%Y M%m",
    ):
        try:
            dt = datetime.strptime(s, fmt)
            return pd.Timestamp(year=dt.year, month=dt.month, day=1)
        except Exception:
            continue

    # Fallback to pandas
    try:
        dt = pd.to_datetime(s, errors="coerce")
        if pd.isna(dt):
            return None
        return pd.Timestamp(year=dt.year, month=dt.month, day=1)
    except Exception:
        return None


def _first_nonnull(iterable, default=None):
    """Return first non-null value from iterable."""
    for x in iterable:
        if x is not None and not (isinstance(x, float) and np.isnan(x)):
            return x
    return default


def _infer_snapshot_date_from_name(name: str) -> pd.Timestamp | None:
    """Extract date from filename like 'alt_fuel_stations (Oct 7 2024).csv'."""
    # First try to find content in parentheses
    import re

    paren_match = re.search(r"\(([^)]+)\)", name)
    if paren_match:
        date_str = paren_match.group(1)
        try:
            dt = pd.to_datetime(date_str, errors="raise")
            return pd.Timestamp(dt.date())
        except Exception:
            pass

    # Fallback: tokenize and try 3-token windows
    name = name.replace("_", " ")
    tokens = [t.strip("() ") for t in name.split()]

    # Try 3-token windows (e.g., 'Oct', '7', '2024')
    for i in range(len(tokens) - 2):
        window = " ".join(tokens[i : i + 3])
        try:
            dt = pd.to_datetime(window, errors="raise")
            return pd.Timestamp(dt.date())
        except Exception:
            continue

    # Fallback: find a year in the name
    for t in tokens:
        if t.isdigit() and len(t) == 4:
            return pd.Timestamp(int(t), 10, 7)  # arbitrary mid-point
    return None


def _parse_nhtsa_date(nhtsa_id: str) -> pd.Timestamp | None:
    """Extract date from NHTSA ID like '20E003' -> 2020."""
    if pd.isna(nhtsa_id):
        return None
    match = re.match(r"(\d{2})[A-Z]", str(nhtsa_id))
    if match:
        year = 2000 + int(match.group(1))
        return pd.Timestamp(year, 1, 1)
    return None


# ---------------------------------------------------------------------------
# AFDC: Historical station snapshots
# ---------------------------------------------------------------------------
def ingest_afdc_historical(files: list[Path]) -> pd.DataFrame:
    """Read and stack multiple AFDC historical CSV snapshots.

    Extracts snapshot date from filename and handles varying column names.
    Returns raw combined DataFrame with 'snapshot_date' column added.
    """
    frames = []
    for f in files:
        if not Path(f).exists():
            log.warning(f"AFDC file missing: {f}")
            continue
        log.info(f"Reading AFDC file: {f.name}")
        df = pd.read_csv(f, low_memory=False)
        df["snapshot_date"] = _infer_snapshot_date_from_name(f.name)
        frames.append(df)

    if not frames:
        log.warning("No AFDC files found")
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    log.info(f"Ingested {len(combined)} AFDC station records")
    return combined


def standardize_afdc(
    df: pd.DataFrame, state_pop: pd.DataFrame = DEFAULT_STATE_POP
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Standardize AFDC data into two outputs.

    Returns:
        (ports_per_100k_df, dcfast_share_df)

    Output schemas:
        - ports_per_100k: state, date, ports_per_100k
        - dcfast_share: state, date, dcfast_share
    """
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # Filter to ELEC stations only
    if "Fuel Type Code" in df.columns:
        df = df[df["Fuel Type Code"].eq("ELEC")].copy()
    else:
        log.warning("No 'Fuel Type Code' column; assuming all ELEC")

    # Find and normalize state column
    state_col = _first_nonnull(
        [c for c in df.columns if c in ("State", "STATE", "state")], "State"
    )
    if state_col not in df.columns:
        raise ValueError("AFDC: could not find 'State' column")

    df = df[df[state_col].isin(STATE_ABBR)].copy()
    df.rename(columns={state_col: "state"}, inplace=True)
    log.info(f"Filtered to {len(df)} AFDC records with valid state codes")

    # Compute port counts with fallback logic
    dc_fast = _find_column(
        df, ["EV DC Fast Count", "EV Fast Count", "EVDC_FastCount"]
    )
    lvl2 = _find_column(
        df, ["EV Level2 EVSE Num", "EV Level 2 EVSE Num", "EV_Level2_EVSENum"]
    )
    lvl1 = _find_column(
        df, ["EV Level1 EVSE Num", "EV Level 1 EVSE Num", "EV_Level1_EVSENum"]
    )

    # Compute total ports
    if dc_fast is not None or lvl2 is not None or lvl1 is not None:
        parts = [
            pd.to_numeric(x, errors="coerce").fillna(0)
            if x is not None
            else pd.Series(0, index=df.index)
            for x in [dc_fast, lvl2, lvl1]
        ]
        ports_series = sum(parts)
        log.info("Using explicit port count columns")
    else:
        # Fallback: count connectors from 'EV Connector Types'
        conn_col = _first_nonnull(
            [c for c in df.columns if "connector" in c.lower()], None
        )
        if conn_col:
            log.info(f"Fallback: counting connectors from '{conn_col}'")
            ports_series = (
                df[conn_col]
                .fillna("")
                .apply(
                    lambda s: (
                        0
                        if s == ""
                        else len([x for x in str(s).split(";") if x.strip()])
                    )
                )
            )
        else:
            log.warning("No port columns found; using 1 per station")
            ports_series = pd.Series(1, index=df.index)

    df["ports"] = ports_series.astype(int)
    df["dc_fast_ports"] = (
        pd.to_numeric(dc_fast, errors="coerce").fillna(0).astype(int)
        if dc_fast is not None
        else 0
    )
    df["snapshot_date"] = pd.to_datetime(
        df.get("snapshot_date"), errors="coerce"
    ).dt.date

    # Aggregate by state and date
    grp = (
        df.groupby(["state", "snapshot_date"], dropna=False)
        .agg(ports=("ports", "sum"), dc_fast_ports=("dc_fast_ports", "sum"))
        .reset_index()
    )

    # Merge with population
    grp = grp.merge(state_pop, on="state", how="left")
    grp["ports_per_100k"] = grp["ports"] / grp["population"] * 100_000
    grp["dcfast_share"] = np.where(
        grp["ports"] > 0, grp["dc_fast_ports"] / grp["ports"], np.nan
    )

    # Output dataframes
    ports_per_100k = grp[["state", "snapshot_date", "ports_per_100k"]].copy()
    dcfast_share = grp[["state", "snapshot_date", "dcfast_share"]].copy()
    ports_per_100k.rename(columns={"snapshot_date": "date"}, inplace=True)
    dcfast_share.rename(columns={"snapshot_date": "date"}, inplace=True)

    log.info(f"AFDC standardized: {len(ports_per_100k)} state-date records")
    return ports_per_100k, dcfast_share


def _find_column(df: pd.DataFrame, candidates: list[str]) -> pd.Series | None:
    """Find first matching column from candidates list."""
    for col in candidates:
        if col in df.columns:
            return df[col]
    return None


# ---------------------------------------------------------------------------
# EIA: Residential electricity price and sales
# ---------------------------------------------------------------------------
def ingest_eia_price(xlsx: Path) -> pd.DataFrame:
    """Parse EIA Table 5.06.A (avg retail price, residential).

    Handles wide format with months as columns; returns tidy:
        state, month, cents_per_kWh
    """
    if not xlsx.exists():
        log.warning(f"EIA price file not found: {xlsx}")
        return pd.DataFrame()

    log.info(f"Reading EIA price file: {xlsx.name}")
    # Read with multi-level headers
    df = pd.read_excel(xlsx, sheet_name=0, header=[2, 3])

    # Find state column (first column)
    state_col = df.columns[0]
    if isinstance(state_col, tuple):
        df["location"] = df[state_col]
    else:
        df.rename(columns={state_col: "location"}, inplace=True)

    # Map state names to abbreviations
    df["state"] = df["location"].map(STATE_NAME_TO_ABBR)
    df = df[df["state"].notna()].copy()

    # Find residential columns
    residential_cols = [
        c
        for c in df.columns
        if isinstance(c, tuple) and "residential" in str(c[0]).lower()
    ]

    if not residential_cols:
        log.warning("EIA price: no Residential columns found")
        return pd.DataFrame()

    # Build tidy format manually to handle tuple columns correctly
    rows = []
    for idx in df.index:
        # Extract state as scalar - use iloc with numeric index
        state = df.loc[idx, "state"]
        # Convert to scalar if it's a Series
        if isinstance(state, pd.Series):
            state = state.iloc[0] if len(state) > 0 else None
        if pd.isna(state):
            continueat
        for col in residential_cols:
            value = df.loc[idx, col]
            # Convert to scalar if needed
            if isinstance(value, pd.Series):
                value = value.iloc[0] if len(value) > 0 else None
            # col is a tuple like ('Residential', '2024-01')
            month_str = col[1] if isinstance(col, tuple) and len(col) > 1 else str(col)
            month = _safe_month_parse(month_str)
            if month is not None and pd.notna(value):
                try:
                    cents = float(value)
                    rows.append({"state": str(state), "month": month, "cents_per_kWh": cents})
                except (ValueError, TypeError):
                    continue
    
    if not rows:
        return pd.DataFrame()
    
    tidy = pd.DataFrame(rows)
    log.info(f"EIA price: parsed {len(tidy)} state-month records")
    return tidy


def ingest_eia_sales(xlsx: Path) -> pd.DataFrame:
    """Parse EIA Table 5.04.B (retail sales & customers).

    Returns tidy format: state, month, MWh
    """
    if not xlsx.exists():
        log.warning(f"EIA sales file not found: {xlsx}")
        return pd.DataFrame()

    log.info(f"Reading EIA sales file: {xlsx.name}")
    # Read with multi-level headers
    df = pd.read_excel(xlsx, sheet_name=0, header=[2, 3])

    # Find state column (first column)
    state_col = df.columns[0]
    if isinstance(state_col, tuple):
        df["location"] = df[state_col]
    else:
        df.rename(columns={state_col: "location"}, inplace=True)

    # Map state names to abbreviations
    df["state"] = df["location"].map(STATE_NAME_TO_ABBR)
    df = df[df["state"].notna()].copy()

    # Find residential columns
    residential_cols = [
        c
        for c in df.columns
        if isinstance(c, tuple) and "residential" in str(c[0]).lower()
    ]

    if not residential_cols:
        log.warning("EIA sales: no Residential columns found")
        return pd.DataFrame()

    # Build tidy format manually to handle tuple columns correctly
    rows = []
    for idx in df.index:
        # Extract state as scalar - use loc with index
        state = df.loc[idx, "state"]
        # Convert to scalar if it's a Series
        if isinstance(state, pd.Series):
            state = state.iloc[0] if len(state) > 0 else None
        if pd.isna(state):
            continue
        for col in residential_cols:
            value = df.loc[idx, col]
            # Convert to scalar if needed
            if isinstance(value, pd.Series):
                value = value.iloc[0] if len(value) > 0 else None
            # col is a tuple like ('Residential', '2024-01')
            month_str = col[1] if isinstance(col, tuple) and len(col) > 1 else str(col)
            month = _safe_month_parse(month_str)
            if month is not None and pd.notna(value):
                try:
                    mwh = float(value)
                    rows.append({"state": str(state), "month": month, "MWh": mwh})
                except (ValueError, TypeError):
                    continue
    
    if not rows:
        return pd.DataFrame()
    
    tidy = pd.DataFrame(rows)
    log.info(f"EIA sales: parsed {len(tidy)} state-month records")
    return tidy


def standardize_eia(
    price_df: pd.DataFrame, sales_df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Standardize EIA data.

    Returns (price_df, sales_df) sorted by state and month.
    """
    price = price_df.copy()
    sales = sales_df.copy()

    # Sort and clean
    price = price.sort_values(["state", "month"]).reset_index(drop=True)
    sales = sales.sort_values(["state", "month"]).reset_index(drop=True)

    # Compute sales per customer if customer count available
    if "customers" in sales.columns:
        sales["MWh_per_customer"] = sales["MWh"] / sales["customers"]
        sales = sales[["state", "month", "MWh_per_customer"]].copy()

    log.info(f"EIA standardized: {len(price)} price, {len(sales)} sales records")
    return price, sales


# ---------------------------------------------------------------------------
# NHTSA: Recalls
# ---------------------------------------------------------------------------
def ingest_recalls(files: list[Path]) -> pd.DataFrame:
    """Read and stack NHTSA recall CSV files.

    Handles varying column names (Make/Manufacturer Name, etc.).
    """
    frames = []
    for f in files:
        if not Path(f).exists():
            log.warning(f"Recall file missing: {f}")
            continue
        log.info(f"Reading recall file: {f.name}")
        df = pd.read_csv(f, low_memory=False)
        frames.append(df)

    if not frames:
        log.warning("No recall files found")
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    log.info(f"Ingested {len(combined)} recall records")
    return combined


def standardize_recalls(
    df: pd.DataFrame, makes: list[str] | None = None
) -> pd.DataFrame:
    """Standardize recalls data.

    Args:
        df: Raw recall DataFrame
        makes: Optional list of makes to filter (e.g., ['RIVIAN', 'TESLA'])

    Returns:
        DataFrame with schema: make, month, recall_count_12m, recalls_per_10k
    """
    if df.empty:
        return pd.DataFrame()

    # Normalize column names
    df.columns = df.columns.str.upper().str.strip()

    # Find make column
    make_col = _first_nonnull(
        [c for c in df.columns if c in ("MAKE", "MANUFACTURER NAME", "MFR_NAME")],
        None,
    )
    if make_col is None:
        log.warning("Recalls: MAKE column not found")
        return pd.DataFrame()

    sdf = df.copy()
    sdf.rename(columns={make_col: "make"}, inplace=True)
    sdf["make"] = sdf["make"].str.upper().str.strip()

    # Filter by makes if specified
    if makes:
        makes_upper = [m.upper() for m in makes]
        sdf = sdf[sdf["make"].isin(makes_upper)].copy()
        log.info(f"Filtered to {len(sdf)} recalls for makes: {makes}")

    # Find date column
    date_col = _first_nonnull(
        [
            c
            for c in sdf.columns
            if any(
                x in c
                for x in (
                    "REPORT RECEIVED DATE",
                    "RECORD CREATION DATE",
                    "DATE",
                    "NHTSA ID",
                )
            )
        ],
        None,
    )

    if date_col and "NHTSA" in date_col:
        # Parse date from NHTSA ID
        sdf["month"] = sdf[date_col].apply(_parse_nhtsa_date)
    elif date_col:
        sdf["month"] = pd.to_datetime(sdf[date_col], errors="coerce").dt.to_period(
            "M"
        ).dt.to_timestamp()
    else:
        log.warning("Recalls: no date column found; cannot compute monthly stats")
        # Fallback to model year aggregation
        if "MODEL YEAR" in sdf.columns:
            yearly = (
                sdf.groupby(["make", "MODEL YEAR"], dropna=False)
                .size()
                .reset_index(name="recall_count")
            )
            return yearly
        else:
            # Just count by make
            totals = (
                sdf.groupby("make", dropna=False)
                .size()
                .reset_index(name="recall_count")
            )
            return totals

    sdf = sdf.dropna(subset=["month"]).copy()

    # Count recalls by make and month
    monthly = (
        sdf.groupby(["make", "month"], dropna=False)
        .size()
        .reset_index(name="recall_count")
    )

    # Compute 12-month rolling sum
    monthly = monthly.sort_values(["make", "month"])
    monthly["recall_count_12m"] = monthly.groupby("make")[
        "recall_count"
    ].transform(lambda x: x.rolling(12, min_periods=1).sum())

    # Compute recalls per 10k (placeholder; needs production volume data)
    # For now, just return the rolling count
    monthly["recalls_per_10k"] = np.nan  # Needs external production data

    log.info(f"Recalls standardized: {len(monthly)} make-month records")
    return monthly[["make", "month", "recall_count_12m", "recalls_per_10k"]]


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
@dataclass
class Paths:
    """Input file paths for ingestion."""

    afdc_files: list[Path]
    eia_price_xlsx: Path
    eia_sales_xlsx: Path
    recall_files: list[Path]
    safercar_csv: Path | None = None


def run_all(paths: Paths, out_dir: Path) -> None:
    """Run complete ingestion and standardization pipeline.

    Args:
        paths: Input file paths (Paths dataclass)
        out_dir: Output directory for processed CSVs
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    log.info(f"Starting ingestion pipeline; output dir: {out_dir}")

    # --- AFDC ---
    log.info("=== Processing AFDC data ===")
    afdc_raw = ingest_afdc_historical(paths.afdc_files)
    if afdc_raw.empty:
        log.warning("AFDC: no data ingested")
        ports_per_100k = pd.DataFrame()
        dcfast_share = pd.DataFrame()
    else:
        ports_per_100k, dcfast_share = standardize_afdc(afdc_raw)
        ports_per_100k.to_csv(
            out_dir / "afdc_ports_per_100k_by_state_year.csv", index=False
        )
        dcfast_share.to_csv(
            out_dir / "afdc_dcfast_share_by_state_year.csv", index=False
        )
        log.info(f"Wrote {len(ports_per_100k)} ports_per_100k rows")
        log.info(f"Wrote {len(dcfast_share)} dcfast_share rows")

    # --- EIA ---
    log.info("=== Processing EIA data ===")
    price = (
        ingest_eia_price(paths.eia_price_xlsx)
        if paths.eia_price_xlsx and paths.eia_price_xlsx.exists()
        else pd.DataFrame()
    )
    sales = (
        ingest_eia_sales(paths.eia_sales_xlsx)
        if paths.eia_sales_xlsx and paths.eia_sales_xlsx.exists()
        else pd.DataFrame()
    )

    if not price.empty and not sales.empty:
        price, sales = standardize_eia(price, sales)

    if not price.empty:
        price.to_csv(
            out_dir / "eia_res_price_residential_state_month.csv", index=False
        )
        log.info(f"Wrote {len(price)} price rows")
    else:
        log.warning("EIA price: no data")

    if not sales.empty:
        sales.to_csv(
            out_dir / "eia_res_sales_per_customer_state_month.csv", index=False
        )
        log.info(f"Wrote {len(sales)} sales rows")
    else:
        log.warning("EIA sales: no data")

    # --- NHTSA Recalls ---
    log.info("=== Processing NHTSA recalls ===")
    recalls = ingest_recalls(paths.recall_files)
    if recalls.empty:
        log.warning("NHTSA recalls: no data")
        recalls_std = pd.DataFrame()
    else:
        # Filter to key EV makes
        recalls_std = standardize_recalls(
            recalls, makes=["RIVIAN", "TESLA", "FORD", "CHEVROLET", "GMC"]
        )
        if not recalls_std.empty:
            recalls_std.to_csv(
                out_dir / "recalls_per_10k_by_make_month_12m.csv", index=False
            )
            log.info(f"Wrote {len(recalls_std)} recall rows")

    # --- Master Panel (state-month join of AFDC + EIA) ---
    log.info("=== Creating master panel ===")
    try:
        if not ports_per_100k.empty and not price.empty:
            # Convert AFDC date to month
            p100k = ports_per_100k.copy()
            p100k["month"] = pd.to_datetime(p100k["date"]).dt.to_period(
                "M"
            ).dt.to_timestamp()

            dfs = dcfast_share.copy()
            dfs["month"] = pd.to_datetime(dfs["date"]).dt.to_period(
                "M"
            ).dt.to_timestamp()

            # Merge on state + month
            master = price.merge(
                p100k.drop(columns=["date"]), on=["state", "month"], how="left"
            )
            master = master.merge(
                dfs.drop(columns=["date"]), on=["state", "month"], how="left"
            )

            if not sales.empty:
                master = master.merge(sales, on=["state", "month"], how="left")

            master.to_csv(out_dir / "master_panel_state_month.csv", index=False)
            log.info(f"Wrote {len(master)} master panel rows")
        else:
            log.warning("Master panel not created (missing AFDC or EIA data)")
    except Exception as e:
        log.error(f"Master panel creation failed: {e}")

    log.info("=== Pipeline complete ===")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    """Run ingestion pipeline with default paths."""
    from pathlib import Path

    base = Path(__file__).parent.parent
    raw_dir = base / "data" / "raw"

    paths = Paths(
        afdc_files=[
            raw_dir / "alt_fuel_stations_historical_day (Oct 7 2021).csv",
            raw_dir / "alt_fuel_stations_historical_day (Oct 7 2022).csv",
            raw_dir / "alt_fuel_stations_historical_day (Oct 7 2023).csv",
            raw_dir / "alt_fuel_stations_historical_day (Oct 7 2024).csv",
        ],
        eia_price_xlsx=raw_dir / "table_5_06_a.xlsx",
        eia_sales_xlsx=raw_dir / "table_5_04_b.xlsx",
        recall_files=[
            raw_dir / "RCL_FROM_2020_2024.csv",
            raw_dir / "RCL_FROM_2025_2025.csv",
        ],
        safercar_csv=raw_dir / "Safercar_data.csv",
    )

    out_dir = base / "data" / "processed"
    run_all(paths, out_dir)

    print("\n✓ Done. Outputs in:", out_dir)
    for f in sorted(out_dir.glob("*.csv")):
        rows = sum(1 for _ in open(f)) - 1  # subtract header
        print(f"  - {f.name} ({rows} rows)")


if __name__ == "__main__":
    main()

