# Data Model

## Tables

| Table | Grain | Rows | Role |
|---|---|---:|---|
| `Fact_Annual` | (Stock, EndDate), annual | 17,511 | Primary fact table — drives Pages 1, 2, 3 and the annual view on Page 4 |
| `Fact_Quarterly` | (Stock, EndDate), quarterly | 17,651 | Secondary fact table — quarterly trend visual on Page 4 only |
| `Dim_Company` | Stock | 4,422 | Company dimension: identity + derived size/profitability/quality attributes |
| `Dim_Date` | Date | one row per calendar day spanning the data | Standard Power BI date table for time-intelligence and consistent axis formatting |

## Why a (small) star schema, not one flat table

The source is close to a single flat table — there is no separate sector, industry or geography dimension to normalise out, because those fields don't exist in the data. A textbook multi-dimension star schema would be over-engineering here.

What *does* justify splitting into a star rather than one merged CSV:
1. **Two fact grains.** Annual and quarterly rows cannot live in one table without a `PeriodType` filter on every measure; two fact tables sharing `Dim_Company` and `Dim_Date` avoid that.
2. **Company attributes are computed once.** `RevenueSizeBand`, `ProfitabilityTier` and `DataCompletenessFlag` are derived from each company's *latest* period. Storing them in `Fact_Annual` would repeat and risk drifting across a company's 4 rows; storing them once in `Dim_Company` keeps them consistent and makes them cheap to slice by.
3. **One shared date table** gives correct axis behaviour (continuous timeline, no gaps) and standard DAX time-intelligence functions for anything that does turn out to be calendar-based (e.g. filtering "FY2019 filings" across both fact tables at once), even though the primary YoY logic uses `FYIndex`/`QIndex` (see below), not calendar time-intelligence.

A snowflake or additional dimensions (industry, geography) were considered and rejected — there is nothing to snowflake out; adding empty or fabricated dimension tables would misrepresent the data.

## Relationships

```text
Dim_Company[Stock]  1 ─────< *  Fact_Annual[Stock]
Dim_Company[Stock]  1 ─────< *  Fact_Quarterly[Stock]
Dim_Date[Date]      1 ─────< *  Fact_Annual[EndDate]
Dim_Date[Date]      1 ─────< *  Fact_Quarterly[EndDate]
```

- All relationships are **single-direction** (Dim → Fact), standard star-schema practice — filters flow from the slicers/dimension tables into both fact tables, and cross-filtering between the two fact tables is never required.
- Cardinality: `Dim_Company[Stock]` is unique (1 row per ticker) → **one-to-many** into each fact table. `Dim_Date[Date]` is unique → **one-to-many** into each fact table's `EndDate`.
- `Fact_Annual` and `Fact_Quarterly` have **no direct relationship** to each other; both filter through `Dim_Company` and `Dim_Date`, which is what a company/date slicer needs and avoids ambiguous multi-fact join paths.

## Why year-over-year uses `FYIndex`, not the date table

Fiscal year-ends are not aligned across companies (audit: ~79% end in December, the rest spread across other months). Power BI's standard time-intelligence functions (`SAMEPERIODLASTYEAR`, `PARALLELPERIOD`, …) assume a shared, gap-free calendar and would silently produce wrong "prior year" values for the ~21% of companies on a non-December fiscal year. Instead, `FYIndex` (1 = a company's earliest available annual period, increasing by 1) is computed once in `python/data_validation.py` and `RevenueGrowthYoY` / `NetIncomeGrowthYoY` are pre-joined against each company's own `FYIndex − 1` row. This is correct for every company regardless of its fiscal calendar, and is documented rather than hidden inside a DAX time-intelligence call that looks standard but would be silently wrong here.

`Dim_Date` is still included and marked as a Power BI **Date Table**, because axis continuity and calendar-based filtering (e.g. "show only FY2019-ending filings") are still useful and correct on a true calendar basis.

## Recommended Power BI model diagram

![Data model diagram](data_model_diagram.svg)

`Dim_Company` and `Dim_Date` sit at "1", `Fact_Annual` and `Fact_Quarterly` at "*"; both fact tables relate only to the two dimensions, never to each other. Source: [`data_model_diagram.svg`](data_model_diagram.svg).

## Storage mode / Power Query

- Import mode (the dataset is static — no benefit from DirectQuery).
- Power Query steps per table: set column types (`EndDate`→Date, ratio columns→Decimal with % or ×  formatting applied in the model, not in Power Query), mark `Dim_Date` as a **Date Table**, mark `Dim_Company[Stock]` and `Dim_Date[Date]` as **not hidden** key columns used in slicers, hide foreign keys (`Fact_*[Stock]`, `Fact_*[EndDate]`) from report view once relationships are built.
- No merges/joins happen in Power Query — that work is already done reproducibly in `python/data_validation.py`, so Power Query's job here is load + type + relationships, not transformation. This keeps the heavy lifting in version-controlled, testable Python rather than opaque M steps.
