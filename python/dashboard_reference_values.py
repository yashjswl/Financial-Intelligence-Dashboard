"""Reference values for checking the Power BI report against the processed data.

Recomputes, independently of Power BI, the figures shown on the dashboard
(latest fiscal year per company): headline KPIs, size-band margins, outlier
fences, the high-margin/low-leverage screen, and a single-company example.
Used to verify DAX measures; also the source of the figures in
docs/KEY_INSIGHTS.md.

Usage:
    python python/dashboard_reference_values.py [--processed data/processed] [--company AAPL]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--processed", default="data/processed")
    ap.add_argument("--company", default="AAPL")
    args = ap.parse_args()
    p = Path(args.processed)

    fact = pd.read_csv(p / "fact_annual.csv")
    dim = pd.read_csv(p / "dim_company.csv")
    latest = fact[fact["IsLatestFY"]].merge(dim[["Stock", "RevenueSizeBand", "DataCompletenessFlag"]], on="Stock")
    ready = latest[latest["DataCompletenessFlag"] == "Analysis-ready"]

    print("== Page 1: headline KPIs (latest FY, all companies) ==")
    print(f"Total Companies        {latest['Stock'].nunique():,}")
    print(f"Total Revenue          {latest['TotalRevenue'].sum() / 1e12:.2f}T")
    print(f"Total Net Income       {latest['NetIncome'].sum() / 1e12:.2f}T")
    print(f"Profit Margin %        {latest['NetIncome'].sum() / latest['TotalRevenue'].sum():.2%}")
    print(f"EBITDA (approx.)       {(latest['EBIT'].sum() + latest['Depreciation'].sum()) / 1e12:.2f}T")
    print(f"Median Revenue         {latest['TotalRevenue'].median() / 1e6:.2f}M")

    print("\n== Page 1/2: size bands ==")
    weighted = latest.groupby("RevenueSizeBand").apply(lambda g: g["NetIncome"].sum() / g["TotalRevenue"].sum(), include_groups=False)
    median = latest[latest["NetMargin"].notna()].groupby("RevenueSizeBand")["NetMargin"].median()
    print(pd.DataFrame({"weighted net margin": weighted.map("{:.2%}".format), "median net margin": median.map("{:.2%}".format)}))

    print("\n== Page 3: outlier fences (analysis-ready, net margin, 3x IQR) ==")
    m = ready["NetMargin"].dropna()
    q1, q3 = m.quantile([0.25, 0.75])
    iqr = q3 - q1
    lo, hi = q1 - 3 * iqr, q3 + 3 * iqr
    print(f"Q1 {q1:.4f}  Q3 {q3:.4f}  IQR {iqr:.4f}  fences {lo:.4f} / {hi:.4f}")
    print(f"Outliers: {int(((m < lo) | (m > hi)).sum())} of {len(m):,}  (below {int((m < lo).sum())}, above {int((m > hi).sum())})")

    print("\n== Page 3: high-margin / low-leverage screen ==")
    ratios = ready[["Stock", "NetMargin", "DebtToAssets"]].dropna()
    p75, p25 = ratios["NetMargin"].quantile(0.75), ratios["DebtToAssets"].quantile(0.25)
    print(f"Exact cut-offs (P75 margin {p75:.4f}, P25 liabilities/assets {p25:.4f}): "
          f"{int(((ratios['NetMargin'] >= p75) & (ratios['DebtToAssets'] <= p25)).sum())} companies")
    print(f"Rounded cut-offs as shown on dashboard (>=16.4%, <=39.2%): "
          f"{int(((ratios['NetMargin'] >= 0.164) & (ratios['DebtToAssets'] <= 0.392)).sum())} companies")

    print(f"\n== Page 4: {args.company} (latest FY) ==")
    row = latest[latest["Stock"] == args.company]
    if row.empty:
        print("company not found")
        return
    r = row.iloc[0]
    band = latest[latest["RevenueSizeBand"] == r["RevenueSizeBand"]]
    print(f"Revenue {r['TotalRevenue'] / 1e9:.2f}bn | net margin {r['NetMargin']:.2%} | ROE {r['ReturnOnEquity']:.2%} | "
          f"revenue growth YoY {r['RevenueGrowthYoY']:.2%} | liabilities/assets {r['DebtToAssets']:.2%}")
    print(f"Peer band {r['RevenueSizeBand']}: median net margin {band['NetMargin'].median():.2%} "
          f"-> variance {(r['NetMargin'] - band['NetMargin'].median()) * 100:+.2f} pts; "
          f"median liabilities/assets {band['DebtToAssets'].median():.2%} "
          f"-> variance {(r['DebtToAssets'] - band['DebtToAssets'].median()) * 100:+.2f} pts")


if __name__ == "__main__":
    main()
