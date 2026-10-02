# DAX Measures

All measures use `Fact_Annual` unless stated. Table/column names match [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md).

## Filter-context convention (read this first)

`Fact_Annual` holds up to 4 fiscal years per company. Pages 1–3 (Executive, Peer & Cohort, Financial Health) are **cross-sectional** — one number per company — so they carry a page-level filter `Fact_Annual[IsLatestFY] = TRUE`. Page 4 (Company Deep Dive) removes that filter to show a company's full history. Measures below are written generically (they use whatever `IsLatestFY`/company/date filters are active); they are not hard-coded to "latest year" so the same measure works correctly on both kinds of page.

KPIs that need employee count, market capitalisation, sector or geography (Revenue per Employee, Company vs. **Industry** Average) are **not implemented** — those fields do not exist in the source data (see [`DATASET_AUDIT.md`](DATASET_AUDIT.md)). Peer comparison instead uses the derived `Dim_Company[RevenueSizeBand]` / `[ProfitabilityTier]` cohorts.

---

## 1. Base measures

```DAX
Total Companies =
DISTINCTCOUNT ( Fact_Annual[Stock] )
```
**Meaning:** number of companies in the current filter context.
**Assumptions:** counts any row present, including limited-data companies unless a `DataCompletenessFlag` slicer is applied.
**Edge cases:** none — `DISTINCTCOUNT` is safe on an empty table (returns 0).

```DAX
Total Revenue =
SUM ( Fact_Annual[TotalRevenue] )
```
**Meaning:** aggregate revenue across the companies/periods in context.
**Assumptions:** all figures assumed to be reported in the same currency (unstated in source — documented limitation).
**Edge cases:** includes 983 rows with revenue = 0 and 23 with revenue < 0 (audit finding #2); they are included in the sum as reported, not excluded, so this measure is a literal total, not a "positive revenue" total.

```DAX
Average Revenue =
AVERAGE ( Fact_Annual[TotalRevenue] )

Median Revenue =
MEDIAN ( Fact_Annual[TotalRevenue] )
```
**Meaning:** central tendency of company revenue; median is reported alongside the average because revenue is heavily right-skewed (WMT ≈ $524B vs. a $1,000 minimum) — the average alone is misleading.
**Edge case:** with 0 rows in context, both return `BLANK()`.

```DAX
Total Net Income =
SUM ( Fact_Annual[NetIncome] )

Average Net Income =
AVERAGE ( Fact_Annual[NetIncome] )

Total EBIT =
SUM ( Fact_Annual[EBIT] )

EBITDA (approx.) =
SUM ( Fact_Annual[EBIT] ) + SUM ( Fact_Annual[Depreciation] )
```
**Meaning of EBITDA (approx.):** the source has no reported EBITDA field, so this is the standard EBIT + Depreciation & Amortisation approximation, computed only because both inputs (`EBIT`, `Depreciation`) are directly reported.
**Assumptions:** `Depreciation` (from the cash-flow statement) is used as a proxy for total D&A; it may not capture amortisation booked outside cash-flow reconciliation for every filer. Labelled "(approx.)" everywhere it appears in the report — never presented as a reported figure.
**Edge cases:** `Depreciation` is 6.4% missing; those rows understate the approximation (SUM ignores blanks rather than propagating them).

```DAX
Total Assets = SUM ( Fact_Annual[TotalAssets] )
Total Liabilities = SUM ( Fact_Annual[TotalLiabilities] )
Total Equity = SUM ( Fact_Annual[TotalEquity] )
Total Free Cash Flow = SUM ( Fact_Annual[FreeCashFlow] )
```

---

## 2. Ratio measures (all use `DIVIDE` — never raw `/`)

```DAX
Profit Margin % =
IF ( [Total Revenue] > 0, DIVIDE ( [Total Net Income], [Total Revenue] ) )

Gross Margin % =
IF ( [Total Revenue] > 0, DIVIDE ( SUM ( Fact_Annual[GrossProfit] ), [Total Revenue] ) )

Operating Margin % =
IF ( [Total Revenue] > 0, DIVIDE ( SUM ( Fact_Annual[OperatingIncome] ), [Total Revenue] ) )

Free Cash Flow Margin % =
IF ( [Total Revenue] > 0, DIVIDE ( [Total Free Cash Flow], [Total Revenue] ) )
```
**Business meaning:** share of revenue converted into profit / gross margin / operating profit / free cash flow at whatever grain (single company, cohort, whole universe) is in context.
**Assumptions:** computed on **aggregated** sums, i.e. a revenue-weighted margin — not an average of each company's own margin (see `Average Company Net Margin %` below for that alternative, which matters when comparing companies of very different sizes).
**Edge cases:** the `IF ( [Total Revenue] > 0, … )` guard returns `BLANK()` when revenue is zero or negative (`DIVIDE` alone only guards against zero, and a negative-revenue company would otherwise show a margin with a flipped sign). This matches the per-row ratio columns built in Python, which are also blank when revenue ≤ 0.

```DAX
Average Company Net Margin % =
AVERAGEX ( Fact_Annual, IF ( Fact_Annual[TotalRevenue] > 0, DIVIDE ( Fact_Annual[NetIncome], Fact_Annual[TotalRevenue] ) ) )

Median Company Net Margin % =
MEDIANX ( Fact_Annual, IF ( Fact_Annual[TotalRevenue] > 0, DIVIDE ( Fact_Annual[NetIncome], Fact_Annual[TotalRevenue] ) ) )
```
**Business meaning:** the typical company's own margin, unweighted by size — a mega-cap and a micro-cap count equally. Use this (not the revenue-weighted `Profit Margin %`) when the question is "how profitable is the typical company in this cohort," not "how profitable is this cohort's combined revenue."
**Edge cases:** `AVERAGEX`/`MEDIANX` skip rows where the guard returns `BLANK` (revenue ≤ 0), so the 1,006 zero-or-negative-revenue rows (audit finding #2) don't distort the result; median is reported alongside the average because of the extreme tail seen in the audit (net margin as low as −24,410%).

```DAX
Return on Assets % =
DIVIDE ( [Total Net Income], [Total Assets] )

Return on Equity % =
DIVIDE (
    CALCULATE ( [Total Net Income], Fact_Annual[TotalEquity] > 0 ),
    CALCULATE ( [Total Equity], Fact_Annual[TotalEquity] > 0 )
)

Debt to Assets % =
DIVIDE ( [Total Liabilities], [Total Assets] )

Debt to Equity =
DIVIDE (
    CALCULATE ( [Total Liabilities], Fact_Annual[TotalEquity] > 0 ),
    CALCULATE ( [Total Equity], Fact_Annual[TotalEquity] > 0 )
)

Asset Turnover =
DIVIDE ( [Total Revenue], [Total Assets] )

Current Ratio =
DIVIDE ( SUM ( Fact_Annual[TotalCurrentAssets] ), SUM ( Fact_Annual[TotalCurrentLiabilities] ) )
```
**Business meaning:** profitability relative to assets/equity, leverage, and short-term liquidity.
**Assumptions:** `Return on Equity %` and `Debt to Equity` exclude negative-equity rows from **both** numerator and denominator (so the ratio is computed on the same set of companies) (audit finding #4: 1,410 annual rows have negative equity, where these ratios are not economically meaningful and would produce misleading signs). This follows the same rule as the per-row `ReturnOnEquity`/`DebtToEquity` columns built in `python/data_validation.py` (undefined when equity ≤ 0); the aggregate measure is a pooled ratio over positive-equity companies, not an average of the per-row values.
**Edge cases:** all `BLANK()` rather than error/infinite when the denominator is 0 or excluded.

---

## 3. Cohort benchmark measures (peer comparison, replacing "industry")

**Model rule:** company-level visuals (tables, scatter points, the company slicer) must use `Dim_Company[Stock]`, not `Fact_Annual[Stock]`. Filters flow from the dimension to the facts, so the benchmark measures below can read the company's `RevenueSizeBand` from `Dim_Company` and then lift the company filter to reach its peers.

```DAX
Peer Median Net Margin % =
VAR PeerBand = SELECTEDVALUE ( Dim_Company[RevenueSizeBand] )
RETURN
    IF (
        NOT ISBLANK ( PeerBand ),
        CALCULATE (
            [Median Company Net Margin %],
            REMOVEFILTERS ( Dim_Company[Stock] ),
            Dim_Company[RevenueSizeBand] = PeerBand
        )
    )
```
**Business meaning:** the median net margin of companies in the *same revenue-size cohort* as the company on the current row. This is the peer benchmark used in place of an industry average.
**Assumptions:** peer group = same `RevenueSizeBand` quintile (computed in `dim_company.csv` from latest-FY revenue); other slicers (e.g. `ProfitabilityTier`, `DataCompletenessFlag`) still apply. The company itself is part of its own peer median. Explicitly not an industry peer group.
**Edge cases:** `BLANK` when the context holds more than one band (e.g. a total row) and for the "Not meaningful (revenue <= 0)" band (no defined margins).

```DAX
Company Net Margin % vs Peer Median =
VAR CompanyMargin = [Average Company Net Margin %]
VAR PeerMedian = [Peer Median Net Margin %]
RETURN
    IF ( NOT ISBLANK ( CompanyMargin ) && NOT ISBLANK ( PeerMedian ), CompanyMargin - PeerMedian )

Company Net Margin % vs Peer Median (%) =
VAR CompanyMargin = [Average Company Net Margin %]
VAR PeerMedian = [Peer Median Net Margin %]
RETURN
    IF ( NOT ISBLANK ( CompanyMargin ) && NOT ISBLANK ( PeerMedian ), DIVIDE ( CompanyMargin - PeerMedian, ABS ( PeerMedian ) ) )
```
**Business meaning:** percentage-point (first) and relative (second) variance of a company's margin from its size-band peer median: "is this company's profitability above or below benchmark?"
**Edge cases:** blank when either side is blank, rather than a false variance; relative variance is blank when the peer median is 0.

```DAX
Company Debt to Assets % vs Peer Median =
VAR PeerBand = SELECTEDVALUE ( Dim_Company[RevenueSizeBand] )
VAR CompanyRatio = [Debt to Assets %]
VAR PeerMedian =
    CALCULATE (
        MEDIANX ( Fact_Annual, DIVIDE ( Fact_Annual[TotalLiabilities], Fact_Annual[TotalAssets] ) ),
        REMOVEFILTERS ( Dim_Company[Stock] ),
        Dim_Company[RevenueSizeBand] = PeerBand
    )
RETURN
    IF (
        NOT ISBLANK ( PeerBand ) && NOT ISBLANK ( CompanyRatio ) && NOT ISBLANK ( PeerMedian ),
        CompanyRatio - PeerMedian
    )
```
**Business meaning:** how a company's leverage (liabilities ÷ assets) compares with same-size peers.

---

## 4. Ranking measures

```DAX
Revenue Rank (Universe) =
IF (
    NOT ISBLANK ( [Total Revenue] ),
    RANKX ( ALLSELECTED ( Dim_Company[Stock] ), [Total Revenue], , DESC, Dense )
)

Net Margin Rank (Universe) =
IF (
    NOT ISBLANK ( [Average Company Net Margin %] ),
    RANKX ( ALLSELECTED ( Dim_Company[Stock] ), [Average Company Net Margin %], , DESC, Dense )
)
```
**Business meaning:** a company's position by revenue or margin across the filtered universe. These two measures are defined in the model; the report's Top 10 tables use Top N filters instead, so they are not displayed on a page. (A peer-cohort rank was drafted but is not included, because it was never validated.)
**Assumptions:** `ALLSELECTED` (not `ALL`) so ranks respect slicers the user has set but ignore the row context of the visual. Rank is computed over `Dim_Company[Stock]`, so a visual using it must have `Dim_Company[Stock]` on its rows.
**Edge cases:** `Dense` ranking so ties share a rank without gaps; the `IF` returns `BLANK` for companies whose measure is undefined (e.g. revenue ≤ 0), so they are not given a misleading rank.

---

## 4b. Outlier flag (design note)

An `Is Outlier (Net Margin)` measure exists in the model: it computed the 3×IQR fences with `PERCENTILEX.INC` over `ALLSELECTED ( Dim_Company[Stock] )`. It is **not used on any page**. When the outlier table was filtered on it, the fences were recalculated from the already-filtered, already-extreme companies, so the flag disagreed with the independent check (for example a 1,756% margin was labelled "Typical"). The report instead applies **fixed fences** to `Profit Margin %`: below **−81.1%** or above **+89.7%**. They are Q1 − 3×IQR and Q3 + 3×IQR of latest-year net margins across the 4,140 analysis-ready companies (Q1 = −7.9%, Q3 = +16.5%, IQR = 24.4 points), reproduced by `python/dashboard_reference_values.py`. 595 companies fall outside them (443 below, 152 above).

---

## 5. Growth measures (pre-computed columns, exposed as measures)

```DAX
Revenue Growth YoY % =
MEDIAN ( Fact_Annual[RevenueGrowthYoY] )

Net Income Growth YoY % =
MEDIAN ( Fact_Annual[NetIncomeGrowthYoY] )
```
**Business meaning:** year-over-year growth versus each company's own prior available fiscal period.
**Assumptions:** computed in `python/data_validation.py` using a per-company `FYIndex` join (not calendar time-intelligence) because fiscal year-ends are not aligned across companies — see [`DATA_MODEL.md`](DATA_MODEL.md) for why. At the single-company grain, `MEDIAN` simply returns that company's one value; at a cohort grain it is the median YoY growth across companies. Median, not average, because growth rates have an extreme tail (the latest-FY maximum is +28,338%) that would dominate any average.
**Edge cases:** blank for each company's first available fiscal year (no prior period to compare — 5,172 of 17,511 annual rows) and blank where the prior period's value is 0 (division guarded at build time).

---

## 6. Formatting & naming conventions applied throughout

- Percent measures multiplied by nothing in DAX — stored as a decimal ratio (e.g. 0.15) and formatted as `%` in the model, so they sum/average correctly.
- Every ratio uses `DIVIDE(...)`, never `a / b`, so a zero or negative denominator returns `BLANK()` instead of an error or a nonsensical Infinity.
- Measure names describe the business quantity, not the formula (`Profit Margin %`, not `NetIncome_div_Revenue`).
- Base measures (`Total Revenue`, `Total Net Income`, …) are reused inside ratio/benchmark/rank measures via variables rather than repeating `SUM(...)`, so a definition only lives in one place.
- No hard-coded constants; cohort thresholds (quintile edges for `RevenueSizeBand`, the 0/5%/15% cut points for `ProfitabilityTier`) are computed once in `python/data_validation.py` and documented in [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md), not re-derived ad hoc in DAX.
