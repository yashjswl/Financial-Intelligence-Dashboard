"""Phase 3 data preparation: raw statements -> clean, modelled CSVs for Power BI.

Reads the six raw statement files, fixes the issues found in the dataset audit
(docs/DATASET_AUDIT.md), merges income + balance + cash flow per frequency,
derives fiscal-period indexes and financial ratios, and writes a small star
schema to data/processed/. Never modifies data/raw/.

Design notes (see docs/DATA_MODEL.md for the full rationale):
  - The source has no company name, sector, industry or geography — only a
    ticker and financial-statement figures. Dim_Company therefore carries
    derived attributes (size band, profitability tier) computed from the
    data itself, not sourced external metadata.
  - Fiscal year-ends are not aligned across companies (~79% end in December,
    the rest do not), so year-over-year comparisons use a per-company
    FYIndex (1 = earliest available period ... N = latest) instead of
    calendar-based time intelligence.
  - Ratios are computed here with explicit guards (matching the DIVIDE()
    semantics used later in DAX) so the same null/undefined rules apply
    whether a number is read from Python or Power BI.

Usage:
    python python/data_validation.py [--raw data/raw] [--out data/processed]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

KEY = ["stock", "endDate"]


def safe_div(num: pd.Series, den: pd.Series, min_den: float = 0.0) -> pd.Series:
    """Like DAX DIVIDE(): NaN where the denominator is missing or <= min_den."""
    den_ok = den.where(den > min_den)
    return num / den_ok


def load_frequency(raw: Path, freq: str) -> pd.DataFrame:
    """Load+merge income/balance/cashflow for one frequency, de-duplicated."""
    inc = pd.read_csv(raw / f"incomeStatementHistory_{freq}.csv", low_memory=False)
    bal = pd.read_csv(raw / f"balanceSheetHistory_{freq}.csv", low_memory=False)
    cfs = pd.read_csv(raw / f"cashflowStatement_{freq}.csv", low_memory=False)

    for name, df in (("income", inc), ("balance", bal), ("cashflow", cfs)):
        before = len(df)
        df.drop_duplicates(inplace=True)
        # For (stock, endDate) keys that still repeat after dropping exact
        # duplicates, keep the row with more non-null values (the populated
        # one, not the all-zero one) — see docs/DATASET_AUDIT.md finding #1.
        if df.duplicated(KEY).any():
            df["_nonnull"] = df.notna().sum(axis=1)
            df.sort_values("_nonnull", ascending=False, inplace=True)
            df.drop_duplicates(KEY, keep="first", inplace=True)
            df.drop(columns="_nonnull", inplace=True)
        after = len(df)
        if before != after:
            print(f"  [{freq}/{name}] dropped {before - after} duplicate rows ({before} -> {after})")

    cfs = cfs.drop(columns=["netIncome"])  # identical to income.netIncome (audit: exact match)
    m = inc.merge(bal, on=KEY, how="inner", suffixes=("", "_bal"))
    m = m.merge(cfs, on=KEY, how="inner", suffixes=("", "_cf"))
    m["endDate"] = pd.to_datetime(m["endDate"], errors="coerce")
    m = m.sort_values(["stock", "endDate"]).reset_index(drop=True)
    return m


def add_fiscal_index(df: pd.DataFrame, col_name: str) -> pd.DataFrame:
    """1 = a company's earliest available period, N = its latest."""
    df = df.copy()
    df[col_name] = df.groupby("stock")["endDate"].rank(method="first").astype(int)
    max_idx = df.groupby("stock")[col_name].transform("max")
    df["IsLatestPeriod"] = df[col_name] == max_idx
    df["PeriodsAvailable"] = max_idx
    return df


def add_ratios(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    rev = df["totalRevenue"]
    ta = df["totalAssets"]
    eq = df["totalStockholderEquity"]
    cl = df["totalCurrentLiabilities"]
    ca = df["totalCurrentAssets"]
    liab = df["totalLiab"]

    df["GrossMargin"] = safe_div(df["grossProfit"], rev)
    df["OperatingMargin"] = safe_div(df["operatingIncome"], rev)
    df["NetMargin"] = safe_div(df["netIncome"], rev)
    df["EffectiveTaxRate"] = safe_div(df["incomeTaxExpense"], df["incomeBeforeTax"])
    df["ReturnOnAssets"] = safe_div(df["netIncome"], ta)
    df["ReturnOnEquity"] = safe_div(df["netIncome"], eq)  # NaN if equity <= 0 (audit finding #4)
    df["AssetTurnover"] = safe_div(rev, ta)
    df["CurrentRatio"] = safe_div(ca, cl)
    df["DebtToAssets"] = safe_div(liab, ta)
    df["DebtToEquity"] = safe_div(liab, eq)
    df["CapEx"] = -df["capitalExpenditures"]  # source stores outflow as negative
    df["FreeCashFlow"] = df["totalCashFromOperatingActivities"] + df["capitalExpenditures"]
    df["FreeCashFlowMargin"] = safe_div(df["FreeCashFlow"], rev)

    # Year-over-year growth vs the company's own prior available period
    # (fiscal-index based, since fiscal year-ends are not calendar-aligned).
    prior = df[["stock", "FYIndex", "totalRevenue", "netIncome"]].copy() if "FYIndex" in df.columns else None
    idx_col = "FYIndex" if "FYIndex" in df.columns else "QIndex"
    prior = df[["stock", idx_col, "totalRevenue", "netIncome"]].copy()
    prior[idx_col] += 1
    prior = prior.rename(columns={"totalRevenue": "_prevRevenue", "netIncome": "_prevNetIncome"})
    df = df.merge(prior, on=["stock", idx_col], how="left")
    df["RevenueGrowthYoY"] = safe_div(df["totalRevenue"] - df["_prevRevenue"], df["_prevRevenue"].abs())
    df["NetIncomeGrowthYoY"] = safe_div(df["netIncome"] - df["_prevNetIncome"], df["_prevNetIncome"].abs())
    df.drop(columns=["_prevRevenue", "_prevNetIncome"], inplace=True)

    return df


ANNUAL_COLS = {
    "stock": "Stock", "endDate": "EndDate", "FYIndex": "FYIndex",
    "IsLatestPeriod": "IsLatestFY", "PeriodsAvailable": "PeriodsAvailable",
    "totalRevenue": "TotalRevenue", "costOfRevenue": "CostOfRevenue", "grossProfit": "GrossProfit",
    "totalOperatingExpenses": "TotalOperatingExpenses", "operatingIncome": "OperatingIncome",
    "ebit": "EBIT", "sellingGeneralAdministrative": "SGA", "researchDevelopment": "ResearchDevelopment",
    "interestExpense": "InterestExpense", "incomeTaxExpense": "IncomeTaxExpense",
    "incomeBeforeTax": "IncomeBeforeTax", "netIncome": "NetIncome",
    "totalAssets": "TotalAssets", "totalLiab": "TotalLiabilities", "totalStockholderEquity": "TotalEquity",
    "totalCurrentAssets": "TotalCurrentAssets", "totalCurrentLiabilities": "TotalCurrentLiabilities",
    "cash": "Cash", "inventory": "Inventory", "netReceivables": "NetReceivables",
    "longTermDebt": "LongTermDebt", "shortLongTermDebt": "ShortTermDebt", "goodWill": "Goodwill",
    "retainedEarnings": "RetainedEarnings",
    "totalCashFromOperatingActivities": "CashFromOperations", "CapEx": "CapEx",
    "depreciation": "Depreciation", "dividendsPaid": "DividendsPaid", "repurchaseOfStock": "StockRepurchases",
    "FreeCashFlow": "FreeCashFlow", "FreeCashFlowMargin": "FreeCashFlowMargin",
    "GrossMargin": "GrossMargin", "OperatingMargin": "OperatingMargin", "NetMargin": "NetMargin",
    "EffectiveTaxRate": "EffectiveTaxRate", "ReturnOnAssets": "ReturnOnAssets", "ReturnOnEquity": "ReturnOnEquity",
    "AssetTurnover": "AssetTurnover", "CurrentRatio": "CurrentRatio", "DebtToAssets": "DebtToAssets",
    "DebtToEquity": "DebtToEquity", "RevenueGrowthYoY": "RevenueGrowthYoY", "NetIncomeGrowthYoY": "NetIncomeGrowthYoY",
}
QUARTERLY_COLS = {
    "stock": "Stock", "endDate": "EndDate", "QIndex": "QIndex",
    "IsLatestPeriod": "IsLatestQuarter", "PeriodsAvailable": "PeriodsAvailable",
    "totalRevenue": "TotalRevenue", "grossProfit": "GrossProfit", "operatingIncome": "OperatingIncome",
    "netIncome": "NetIncome", "totalAssets": "TotalAssets", "totalStockholderEquity": "TotalEquity",
    "totalCashFromOperatingActivities": "CashFromOperations", "CapEx": "CapEx", "FreeCashFlow": "FreeCashFlow",
    "GrossMargin": "GrossMargin", "OperatingMargin": "OperatingMargin", "NetMargin": "NetMargin",
    "RevenueGrowthYoY": "RevenueGrowthYoQ", "NetIncomeGrowthYoY": "NetIncomeGrowthYoQ",
}


def size_band(rev: pd.Series) -> pd.Series:
    # Quintiles computed only over companies with positive latest-FY revenue.
    valid = rev[rev > 0]
    edges = valid.quantile([0.2, 0.4, 0.6, 0.8]).values
    labels = ["1 - Micro", "2 - Small", "3 - Mid", "4 - Large", "5 - Mega"]
    bands = pd.cut(rev, bins=[-np.inf, *edges, np.inf], labels=labels)
    return bands.astype(str).where(rev > 0, "Not meaningful (revenue <= 0)")


def profitability_tier(margin: pd.Series) -> pd.Series:
    bins = [-np.inf, 0, 0.05, 0.15, np.inf]
    labels = ["Loss-making (<=0%)", "Low (0-5%)", "Moderate (5-15%)", "High (>15%)"]
    tier = pd.cut(margin, bins=bins, labels=labels)
    return tier.astype(str).where(margin.notna(), "Not meaningful (revenue <= 0)")


def build_dim_company(fact_annual: pd.DataFrame) -> pd.DataFrame:
    latest = fact_annual[fact_annual["IsLatestFY"]].copy()
    dim = latest[[
        "stock", "PeriodsAvailable", "endDate", "totalRevenue", "netIncome", "totalAssets",
        "NetMargin",
    ]].rename(columns={
        "stock": "Stock", "PeriodsAvailable": "PeriodsAvailableAnnual", "endDate": "LatestFYEndDate",
        "totalRevenue": "LatestFYRevenue", "netIncome": "LatestFYNetIncome", "totalAssets": "LatestFYTotalAssets",
        "NetMargin": "LatestFYNetMargin",
    })
    first = fact_annual.groupby("stock")["endDate"].min().rename("FirstFYEndDate")
    dim = dim.merge(first, left_on="Stock", right_index=True)

    dim["RevenueSizeBand"] = size_band(dim["LatestFYRevenue"])
    dim["ProfitabilityTier"] = profitability_tier(dim["LatestFYNetMargin"])
    dim["HasFullHistory4FY"] = dim["PeriodsAvailableAnnual"] >= 4
    latest_all_valid = (
        (dim["LatestFYRevenue"] > 0) & (dim["LatestFYTotalAssets"] > 0)
    )
    dim["DataCompletenessFlag"] = np.where(latest_all_valid, "Analysis-ready", "Limited (zero/negative revenue or assets)")
    return dim[[
        "Stock", "FirstFYEndDate", "LatestFYEndDate", "PeriodsAvailableAnnual", "HasFullHistory4FY",
        "LatestFYRevenue", "LatestFYNetIncome", "LatestFYTotalAssets", "LatestFYNetMargin",
        "RevenueSizeBand", "ProfitabilityTier", "DataCompletenessFlag",
    ]]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--out", default="data/processed")
    args = ap.parse_args()
    raw, out = Path(args.raw), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print("Annual:")
    ann = load_frequency(raw, "annually")
    ann = add_fiscal_index(ann, "FYIndex")
    ann = add_ratios(ann)
    fact_annual = ann.rename(columns=ANNUAL_COLS)[list(ANNUAL_COLS.values())]
    fact_annual.to_csv(out / "fact_annual.csv", index=False)
    print(f"  -> fact_annual.csv: {len(fact_annual):,} rows, {fact_annual['Stock'].nunique():,} companies")

    print("Quarterly:")
    qtr = load_frequency(raw, "quarterly")
    qtr = add_fiscal_index(qtr, "QIndex")
    qtr = add_ratios(qtr)
    fact_quarterly = qtr.rename(columns=QUARTERLY_COLS)[list(QUARTERLY_COLS.values())]
    fact_quarterly.to_csv(out / "fact_quarterly.csv", index=False)
    print(f"  -> fact_quarterly.csv: {len(fact_quarterly):,} rows, {fact_quarterly['Stock'].nunique():,} companies")

    dim_company = build_dim_company(ann.rename(columns={"IsLatestPeriod": "IsLatestFY"}))
    dim_company.to_csv(out / "dim_company.csv", index=False)
    print(f"  -> dim_company.csv: {len(dim_company):,} companies")
    print(dim_company["RevenueSizeBand"].value_counts())
    print(dim_company["ProfitabilityTier"].value_counts())
    print(dim_company["DataCompletenessFlag"].value_counts())


if __name__ == "__main__":
    main()
