"""Read-only audit of the raw Kaggle CSV files.

Profiles each file (shape, dtypes, missing values, duplicates, key cardinality,
period coverage, outliers) and runs cross-file and accounting-identity checks.
Writes a Markdown report; never modifies data/raw/.

Usage:
    python python/data_audit.py [--raw data/raw] [--output docs/audit_output.md]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

KEY = ["stock", "endDate"]
FILES = {
    "income_annual": "incomeStatementHistory_annually.csv",
    "income_quarterly": "incomeStatementHistory_quarterly.csv",
    "balance_annual": "balanceSheetHistory_annually.csv",
    "balance_quarterly": "balanceSheetHistory_quarterly.csv",
    "cashflow_annual": "cashflowStatement_annually.csv",
    "cashflow_quarterly": "cashflowStatement_quarterly.csv",
}
TICKER_OK = re.compile(r"^[A-Z]{1,5}$")


def md_table(df: pd.DataFrame, index: bool = True) -> str:
    """Render a DataFrame as a GitHub-flavoured Markdown table (no tabulate needed)."""
    d = df.reset_index() if index else df
    header = "| " + " | ".join(str(c) for c in d.columns) + " |"
    sep = "|" + "|".join("---" for _ in d.columns) + "|"
    rows = ["| " + " | ".join(str(v) for v in r) + " |" for r in d.itertuples(index=False)]
    return "\n".join([header, sep, *rows])


def fmt(x):
    if isinstance(x, (float, np.floating)):
        return f"{x:,.4g}" if abs(x) < 1e6 else f"{x:,.0f}"
    return x


def load(raw: Path) -> dict[str, pd.DataFrame]:
    out = {}
    for name, fname in FILES.items():
        df = pd.read_csv(raw / fname, low_memory=False)
        df["_endDate_parsed"] = pd.to_datetime(df["endDate"], errors="coerce")
        out[name] = df
    return out


def profile_file(name: str, df: pd.DataFrame, lines: list[str]) -> None:
    d = df.drop(columns="_endDate_parsed")
    lines.append(f"\n## {name}  ({FILES[name]})\n")
    lines.append(f"- Rows: **{len(d):,}**  |  Columns: **{d.shape[1]}**")
    lines.append(f"- Full-row duplicates: **{int(d.duplicated().sum()):,}**")
    lines.append(f"- Duplicate ({', '.join(KEY)}) keys: **{int(d.duplicated(KEY).sum()):,}**")
    lines.append(f"- Unique tickers (`stock`): **{d['stock'].nunique():,}**")
    bad_dates = int(df["_endDate_parsed"].isna().sum())
    lines.append(f"- Unparseable `endDate`: **{bad_dates}**")
    lines.append(
        f"- endDate range: **{df['_endDate_parsed'].min().date()} → {df['_endDate_parsed'].max().date()}**"
    )
    tick = d["stock"].astype(str)
    odd = tick[~tick.str.match(TICKER_OK)]
    lines.append(f"- Tickers not matching `^[A-Z]{{1,5}}$`: **{odd.nunique()}** (e.g. {', '.join(odd.unique()[:8]) or 'none'})")
    ws = int((tick != tick.str.strip()).sum())
    lines.append(f"- Tickers with leading/trailing whitespace: **{ws}**")

    stats = pd.DataFrame(
        {
            "dtype": d.dtypes.astype(str),
            "missing": d.isna().sum(),
            "missing_%": (d.isna().mean() * 100).round(1),
            "unique": d.nunique(),
        }
    )
    num = d.select_dtypes("number")
    if not num.empty:
        q = num.quantile([0.01, 0.5, 0.99]).T
        stats["p01"] = q[0.01]
        stats["median"] = q[0.5]
        stats["p99"] = q[0.99]
        stats["min"] = num.min()
        stats["max"] = num.max()
        stats["negatives"] = (num < 0).sum()
        stats["zeros"] = (num == 0).sum()
    lines.append("\n" + md_table(stats.map(fmt)) + "\n")


def period_coverage(data: dict[str, pd.DataFrame], lines: list[str]) -> None:
    lines.append("\n# Period coverage\n")
    for name in ("income_annual", "income_quarterly"):
        df = data[name]
        per = df.groupby("stock").size()
        lines.append(f"\n### {name}: periods per ticker\n")
        lines.append(md_table(per.describe().to_frame("periods").T.map(fmt)))
        lines.append("\nDistribution of period counts:\n")
        lines.append(md_table(per.value_counts().sort_index().rename("tickers").to_frame().T))
        lines.append(f"\nRows by calendar year of endDate:\n")
        lines.append(md_table(df["_endDate_parsed"].dt.year.value_counts().sort_index().rename("rows").to_frame().T))
        lines.append("\nRows by month of endDate:\n")
        lines.append(md_table(df["_endDate_parsed"].dt.month.value_counts().sort_index().rename("rows").to_frame().T))
        latest = df.groupby("stock")["_endDate_parsed"].max()
        lines.append("\nMost recent period per ticker (top values):\n")
        lines.append(md_table(latest.dt.date.value_counts().head(8).rename("tickers").to_frame().T))


def cross_file(data: dict[str, pd.DataFrame], lines: list[str]) -> None:
    lines.append("\n# Cross-file consistency\n")
    for freq in ("annual", "quarterly"):
        i, b, c = (data[f"{s}_{freq}"] for s in ("income", "balance", "cashflow"))
        ki, kb, kc = (set(map(tuple, x[KEY].astype(str).values)) for x in (i, b, c))
        lines.append(f"\n### {freq}")
        lines.append(f"- (stock, endDate) keys: income={len(ki):,}, balance={len(kb):,}, cashflow={len(kc):,}")
        lines.append(f"- In all three: **{len(ki & kb & kc):,}**")
        lines.append(f"- Income only / not in balance: {len(ki - kb):,}; not in cashflow: {len(ki - kc):,}")
        si, sb, sc = (set(x['stock']) for x in (i, b, c))
        lines.append(f"- Tickers: income={len(si):,}, balance={len(sb):,}, cashflow={len(sc):,}, union={len(si|sb|sc):,}, intersection={len(si&sb&sc):,}")
        m = i.merge(c, on=KEY, suffixes=("_is", "_cf"))[["netIncome_is", "netIncome_cf"]].dropna()
        diff = (m["netIncome_is"] - m["netIncome_cf"]).abs()
        lines.append(f"- netIncome (income vs cashflow) on matched keys: n={len(m):,}, exact matches={int((diff == 0).sum()):,}, differ by >1% of |income|: {int((diff > 0.01 * m['netIncome_is'].abs().clip(lower=1)).sum()):,}")
    a, q = data["income_annual"], data["income_quarterly"]
    lines.append(f"\n- Annual vs quarterly: tickers in both = {len(set(a['stock']) & set(q['stock'])):,}")


def accounting_checks(data: dict[str, pd.DataFrame], lines: list[str]) -> None:
    lines.append("\n# Accounting sanity checks (annual)\n")
    b, i = data["balance_annual"], data["income_annual"]

    rhs = b["totalLiab"] + b["totalStockholderEquity"] + b["minorityInterest"].fillna(0)
    ok = b["totalAssets"].notna() & rhs.notna() & (b["totalAssets"].abs() > 0)
    rel = ((b["totalAssets"] - rhs).abs() / b["totalAssets"].abs())[ok]
    lines.append(f"- Balance identity Assets = Liabilities + Equity (+minority): testable rows={int(ok.sum()):,}; within 1%: {int((rel <= 0.01).sum()):,}; off by >1%: {int((rel > 0.01).sum()):,}; off by >10%: {int((rel > 0.10).sum()):,}")
    for col in ("totalAssets", "totalLiab", "cash", "longTermDebt"):
        lines.append(f"- balance `{col}`: missing={int(b[col].isna().sum()):,}, <0={int((b[col] < 0).sum()):,}, ==0={int((b[col] == 0).sum()):,}")
    lines.append(f"- balance `totalStockholderEquity`: missing={int(b['totalStockholderEquity'].isna().sum()):,}, <0 (negative equity)={int((b['totalStockholderEquity'] < 0).sum()):,}, ==0={int((b['totalStockholderEquity'] == 0).sum()):,}")

    gp = i["totalRevenue"] - i["costOfRevenue"]
    okg = i["grossProfit"].notna() & gp.notna()
    lines.append(f"- grossProfit = revenue - costOfRevenue: testable={int(okg.sum()):,}; exact={int((i['grossProfit'][okg] == gp[okg]).sum()):,}")
    oi = i["totalRevenue"] - i["totalOperatingExpenses"]
    oko = i["operatingIncome"].notna() & oi.notna()
    lines.append(f"- operatingIncome = revenue - totalOperatingExpenses: testable={int(oko.sum()):,}; exact={int((i['operatingIncome'][oko] == oi[oko]).sum()):,}")
    lines.append(f"- ebit == operatingIncome: testable={int((i['ebit'].notna() & i['operatingIncome'].notna()).sum()):,}; equal={int((i['ebit'] == i['operatingIncome']).sum()):,}")
    for col in ("totalRevenue", "netIncome", "grossProfit", "operatingIncome", "ebit", "interestExpense"):
        lines.append(f"- income `{col}`: missing={int(i[col].isna().sum()):,}, <0={int((i[col] < 0).sum()):,}, ==0={int((i[col] == 0).sum()):,}")
    lines.append(f"- interestExpense sign: <0 = {int((i['interestExpense'] < 0).sum()):,}, >0 = {int((i['interestExpense'] > 0).sum()):,} (sign convention check)")
    lines.append(f"- costOfRevenue sign: <0 = {int((i['costOfRevenue'] < 0).sum()):,}, >0 = {int((i['costOfRevenue'] > 0).sum()):,}")


def outliers(data: dict[str, pd.DataFrame], lines: list[str]) -> None:
    lines.append("\n# Outlier scan (annual)\n")
    i, b = data["income_annual"], data["balance_annual"]
    m = i.merge(b, on=KEY, how="inner", suffixes=("", "_bs"))
    m = m[(m["totalRevenue"] > 0)]
    m["net_margin"] = m["netIncome"] / m["totalRevenue"]
    m["gross_margin"] = m["grossProfit"] / m["totalRevenue"]
    m["liab_to_assets"] = m["totalLiab"] / m["totalAssets"].where(m["totalAssets"] > 0)
    m["asset_turnover"] = m["totalRevenue"] / m["totalAssets"].where(m["totalAssets"] > 0)
    m["roe"] = m["netIncome"] / m["totalStockholderEquity"].where(m["totalStockholderEquity"] > 0)
    cols = ["net_margin", "gross_margin", "liab_to_assets", "asset_turnover", "roe"]
    lines.append(f"Rows with revenue>0 in both income and balance: {len(m):,}\n")
    lines.append(md_table(m[cols].describe(percentiles=[0.01, 0.05, 0.5, 0.95, 0.99]).T.map(fmt)))
    for c in cols:
        s = m[c].replace([np.inf, -np.inf], np.nan).dropna()
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        n_out = int(((s < q1 - 3 * iqr) | (s > q3 + 3 * iqr)).sum())
        lines.append(f"- `{c}`: {n_out:,} rows beyond 3×IQR fences ({n_out / len(s):.1%})")
    lines.append("\nLargest |net_margin| rows (stock, endDate, revenue, netIncome, net_margin):\n")
    top = m.reindex(m["net_margin"].abs().sort_values(ascending=False).index).head(8)
    lines.append(md_table(top[["stock", "endDate", "totalRevenue", "netIncome", "net_margin"]].map(fmt), index=False))
    lines.append("\nLargest revenues (annual):\n")
    top = i.sort_values("totalRevenue", ascending=False).head(8)
    lines.append(md_table(top[["stock", "endDate", "totalRevenue", "netIncome"]].map(fmt), index=False))
    lines.append("\nSmallest positive revenues (annual):\n")
    top = i[i["totalRevenue"] > 0].sort_values("totalRevenue").head(8)
    lines.append(md_table(top[["stock", "endDate", "totalRevenue", "netIncome"]].map(fmt), index=False))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--output", default="docs/audit_output.md")
    args = ap.parse_args()

    data = load(Path(args.raw))
    lines: list[str] = ["# Raw audit output (auto-generated by python/data_audit.py)\n"]
    for name, df in data.items():
        profile_file(name, df, lines)
    period_coverage(data, lines)
    cross_file(data, lines)
    accounting_checks(data, lines)
    outliers(data, lines)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
