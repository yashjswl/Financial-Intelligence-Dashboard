# Power BI report

The report was built in the **Power BI service** (browser) on top of a semantic model loaded from the processed CSVs in [`data/processed/`](../data/processed/), then downloaded as [`Public_Company_Financial_Intelligence.pbix`](Public_Company_Financial_Intelligence.pbix) (4 pages, 50 visuals). It opens in Power BI Desktop. The file embeds the processed data, so it is self-contained. Screenshots of all four pages are in [`screenshots/`](../screenshots/) and the layout is documented in [`docs/DASHBOARD_DESIGN.md`](../docs/DASHBOARD_DESIGN.md).

## What the model contains

| Item | Detail |
|---|---|
| Tables | `fact_annual` (17,511 rows), `fact_quarterly` (17,651), `dim_company` (4,422), `Dim_Date` (calculated) |
| Relationships | `dim_company[Stock]` → `fact_annual[Stock]`, `dim_company[Stock]` → `fact_quarterly[Stock]`, `Dim_Date[Date]` → `fact_annual[EndDate]`, `Dim_Date[Date]` → `fact_quarterly[EndDate]`; all one-to-many, single direction |
| Date table | `Dim_Date`, marked as the date table (definition below) |
| Measures | 32, defined in [`docs/DAX_MEASURES.md`](../docs/DAX_MEASURES.md) |
| Page filters | Pages 1–2: `IsLatestFY = True`. Page 3: `IsLatestFY = True` and `DataCompletenessFlag = Analysis-ready`. Page 4: none (full history); its KPI cards carry a visual-level `IsLatestFY = True` filter |

```DAX
Dim_Date =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2012, 1, 1 ), DATE ( 2020, 12, 31 ) ),
    "Year", YEAR ( [Date] ),
    "Quarter", "Q" & QUARTER ( [Date] ),
    "MonthNumber", MONTH ( [Date] ),
    "MonthName", FORMAT ( [Date], "MMM" )
)
```

## Reproducing the report

1. Build the processed data: `python python/data_validation.py` (needs the raw Kaggle files; see [`data/raw/README.md`](../data/raw/README.md)).
2. Load the three CSVs into a Power BI semantic model (Import mode); set `EndDate`, `FirstFYEndDate` and `LatestFYEndDate` to Date and the `Is…` / `Has…` columns to True/False.
3. Add `Dim_Date`, mark it as the date table, and create the four relationships above.
4. Add the measures from `docs/DAX_MEASURES.md`.
5. Lay out the pages as described in `docs/DASHBOARD_DESIGN.md`.
6. Check the result against `python python/dashboard_reference_values.py`, which recomputes the headline KPIs, size-band margins, outlier fences and a sample company independently of Power BI.

## Refresh

The source is a static 2012–2020 extract, so there is no live source to schedule a refresh against. A newer export of the same dataset can be processed by re-running `python/data_validation.py`; the model and measures do not change.
