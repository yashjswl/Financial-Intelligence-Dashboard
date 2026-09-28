# Dataset Audit

Source: *Financial Data of 4400 Public Companies* (Kaggle, `qks1lver`). All figures below were produced by [`python/data_audit.py`](../python/data_audit.py) (full raw output: [`audit_output.md`](audit_output.md)) plus a few targeted follow-up queries. Nothing in this document is assumed.

## 1. What the dataset actually is

Six CSV files: three financial statements × two frequencies. Every row is one **company-period**, identified by `stock` (ticker) and `endDate` (period end).

| File | Rows | Cols | Tickers | endDate range |
|---|---:|---:|---:|---|
| `incomeStatementHistory_annually.csv` | 17,511 | 20 | 4,422 | 2012-07-12 → 2020-05-02 |
| `balanceSheetHistory_annually.csv` | 17,511 | 31 | 4,422 | 2012-07-12 → 2020-05-02 |
| `cashflowStatement_annually.csv` | 17,511 | 22 | 4,422 | 2012-07-12 → 2020-05-02 |
| `incomeStatementHistory_quarterly.csv` | 17,657 | 20 | 4,420 | 2014-09-30 → 2020-05-29 |
| `balanceSheetHistory_quarterly.csv` | 17,657 | 31 | 4,420 | 2014-09-30 → 2020-05-29 |
| `cashflowStatement_quarterly.csv` | 17,657 | 22 | 4,420 | 2014-09-30 → 2020-05-29 |

**Company universe: 4,422 tickers** (annual). The name "4,400 companies" checks out.

### Critical finding: fields the project brief assumed that do **not** exist

| Expected | Present? |
|---|---|
| Company name | ❌ ticker only |
| Sector / industry | ❌ |
| Geography / country / exchange | ❌ |
| Market capitalisation, stock price | ❌ |
| Employees | ❌ |
| Explicit EBITDA | ❌ (EBIT and cash-flow `depreciation` exist, so EBITDA is only an approximation) |
| Explicit "total debt" | ❌ (`longTermDebt` and `shortLongTermDebt` exist, both heavily missing) |
| Multiple time periods | ✅ up to 4 fiscal years (annual), ~4 quarters (quarterly) |

**Consequence:** industry/sector benchmarking, sector slicers, peer groups by industry and geography maps **cannot be built from this dataset alone**. See the decision note in the summary.

## 2. Keys and structure

- `stock` (text, no whitespace issues) + `endDate` (text, `YYYY-MM-DD`, 0 unparseable) form the key.
- **Annual files:** 0 duplicate keys, 0 full-row duplicates. The key sets of income, balance and cash flow are **identical** (17,511 keys in all three).
- **Quarterly files:** 6 duplicate `(stock, endDate)` keys per file; 1 (income), 5 (balance) and 1 (cash flow) are exact duplicate rows. Following up on the income file:
  - 4 keys (AZO, SXT, TRC, VRTU) are exact duplicate rows → safe to drop.
  - 2 keys (BOX 2019-10-31, LHX 2019-09-27) have one populated row and one row of zeros → keep the populated one.
- Ticker format: 4,419 tickers are 1–5 upper-case letters; 3 are share-class tickers with a hyphen (`CRD-A`, `GTN-A`, `LGF-A`). These are valid, not errors.
- Cross-file check: `netIncome` in the income and cash-flow files matches **exactly** on all 17,511 annual keys (4 of ~17,669 quarterly matches differ by >1%, which is the same duplicate-key issue).

## 3. Time coverage

| | Annual | Quarterly |
|---|---|---|
| Tickers with 4 periods | 4,279 (96.8%) | 4,408 (99.7%) |
| 3 / 2 / 1 periods | 114 / 24 / 5 | 2 / 9 / 1 |
| Calendar years of `endDate` | 2016: 3,947 · 2017: 4,425 · 2018: 4,436 · 2019: 4,387 · 2020: 281 (rest: 35 rows pre-2016) | 2019: 13,252 · 2020: 4,322 |
| Most common latest period | 2019-12-31 (3,335 tickers) | 2020-03-31 (3,476 tickers) |

- Fiscal year-end is **not** uniform: 13,802 of 17,511 annual rows end in December, the rest are spread across other months (e.g. WMT ends January). Fiscal years must be assigned from `endDate`, not assumed to be calendar years. Consecutive annual periods are ~365 days apart (52 gaps fall outside 350–380 days).
- **The data is a static snapshot ending mid-2020** (files dated 14 Jun 2020). It is not live and contains no post-2020 information.
- **Implication for analysis:** only ~4 annual observations per company, so YoY growth is valid (3 growth points per company at most), but a multi-year CAGR would rest on a 3-year window at most.

## 4. Column inventory and data types

All numeric statement fields are stored as numbers in **whole currency units** (e.g. WMT FY2020 revenue = 523,964,000,000, i.e. ≈ $524B, consistent with USD reporting, not thousands). The currency is not stated in the files; no currency column exists. Some tickers are foreign issuers/ADRs (e.g. BP), so the assumption "everything is USD" is plausible but **unverifiable from the file**.

Type issues: `endDate` is text (needs conversion to date). Several income fields are `int64` (no nulls); most balance/cash-flow fields are `float64` because of missing values.

### Income statement (20 cols)

`stock, endDate, netIncomeApplicableToCommonShares, netIncomeFromContinuingOps, totalOtherIncomeExpenseNet, costOfRevenue, totalOperatingExpenses, totalRevenue, incomeTaxExpense, interestExpense, operatingIncome, ebit, grossProfit, sellingGeneralAdministrative, netIncome, incomeBeforeTax, researchDevelopment, otherOperatingExpenses, minorityInterest, discontinuedOperations`

| Field | Missing % (annual) | Notes |
|---|---:|---|
| `totalRevenue`, `netIncome`, `grossProfit`, `operatingIncome`, `ebit`, `costOfRevenue`, `incomeTaxExpense` | 0.0 | Fully populated |
| `sellingGeneralAdministrative` | 1.3 | |
| `interestExpense` | 25.2 | Stored as a **negative** number in 13,077 of 13,090 populated rows |
| `researchDevelopment` | 66.3 | Only meaningful for R&D-reporting firms |
| `otherOperatingExpenses` / `minorityInterest` | 70.1 / 68.9 | |
| `discontinuedOperations` | 91.2 | |

### Balance sheet (31 cols)

Key fields: `totalAssets` (1.0% missing), `totalLiab` (1.1%), `totalStockholderEquity` (0.9%), `totalCurrentAssets` (1.0%), `totalCurrentLiabilities` (1.1%), `cash` (3.3%), `netReceivables` (16.9%), `inventory` (44.9%), `longTermDebt` (35.9%), `shortLongTermDebt` (69.0%), `goodWill` (44.8%), `minorityInterest` (74.8%).

Debt fields are **missing far too often to be read as "zero debt"**: a blank could mean no debt or not reported; the file does not say.

### Cash flow (22 cols)

Key fields: `totalCashFromOperatingActivities` (1.7% missing), `capitalExpenditures` (12.8%), `depreciation` (6.4%), `dividendsPaid` (52.1%), `repurchaseOfStock` (40.3%), `netIncome` (0%).

Full per-column tables (dtype, missing, unique, p01/median/p99/min/max, negatives, zeros) for all six files are in [`audit_output.md`](audit_output.md).

## 5. Data-quality findings

| # | Finding | Evidence | Treatment (proposed) |
|---|---|---|---|
| 1 | Duplicate quarterly keys | 6 keys per quarterly file; 4 exact duplicates + 2 populated/all-zero pairs in income | Drop exact duplicates; keep populated row of a zero pair |
| 2 | Zero/negative revenue | 983 annual rows with revenue = 0, 23 with revenue < 0; **198 tickers have revenue ≤ 0 in every annual period** | Exclude from margin/turnover measures (ratio undefined), keep in counts; cause (pre-revenue firms, banks reporting differently, or missing data) cannot be determined from the file, so do not label |
| 3 | Balance identity breaks | Assets ≠ Liabilities + Equity (+ minority) by >1% in 1,807 of 17,315 testable rows (990 by >10%); 430 of the 1,807 have a minority-interest value | Flag, do not correct; likely mezzanine/redeemable items not captured. Ratios use reported totals |
| 4 | Negative equity | 1,410 annual rows | Return-on-equity and debt-to-equity are not meaningful → return BLANK |
| 5 | Extreme ratios | Net margin p01 = −8,840%, min = −2,441,000% (ALBO 2017: revenue $1,000, net loss $24.4M); ROE max ≈ 1.9M× | Tiny denominators, not errors. Use medians and capped/winsorised views; never average raw ratios |
| 6 | EBIT ≠ operating income | Differ in 1,878 of 17,511 rows | Use `operatingIncome` for operating margin (it reconciles to revenue − total operating expenses in 17,498 of 17,511 rows) |
| 7 | Sign conventions | `interestExpense` negative; `capitalExpenditures`, `dividendsPaid`, `repurchaseOfStock` negative (outflows); `costOfRevenue` positive (4 negative rows) | Document; use ABS where needed |
| 8 | Fiscal-year misalignment | 79% of annual periods end in December; others differ | Define `FiscalYear` from `endDate`; label as "fiscal year ending" |
| 9 | Incomplete history | 143 tickers (3.2%) have fewer than 4 annual periods | Growth measures blank where the prior period is missing |
| 10 | Latest period varies | Latest annual `endDate` is 2019 for 4,105 tickers, 2020 for 281, 2018 for 35, 2015 for 1 | "Latest FY" is per company; label accordingly |
| 11 | Currency unstated | No currency column | Document assumption; do not sum across currencies without caveat |
| 12 | Survivorship | Set of tickers with data in 2020 | Only firms alive in 2020; cannot describe delisted firms |

### Comparable-sample sizes (latest annual period per ticker)

| Population | Count |
|---|---:|
| All tickers | 4,422 |
| Revenue > 0 | 4,181 |
| Total assets > 0 | 4,378 |
| Revenue > 0, assets > 0 **and** equity > 0 (full ratio set usable) | 3,905 |

## 6. Business interpretation of fields

- **Size:** `totalRevenue`, `totalAssets`.
- **Profitability:** `grossProfit`, `operatingIncome`, `ebit`, `netIncome` → margins.
- **Leverage / solvency:** `totalLiab`, `totalStockholderEquity`, `totalAssets`, `longTermDebt` (sparse).
- **Liquidity:** `totalCurrentAssets`, `totalCurrentLiabilities`, `cash`.
- **Cash generation & investment:** `totalCashFromOperatingActivities`, `capitalExpenditures` (→ free cash flow), `depreciation`.
- **Shareholder returns:** `dividendsPaid`, `repurchaseOfStock` (sparse).
- **Time:** `endDate`; annual vs quarterly frequency.

Not derivable: valuation multiples, per-employee productivity, market-share, sector benchmarks.

## 7. Categorical dimensions available

Only `stock` (4,422 values) and time (`endDate`). There are **no** natural categorical dimensions beyond these. Any grouping (size bands, profitability bands, growth bands) would be *derived* from the financials, not sourced.
