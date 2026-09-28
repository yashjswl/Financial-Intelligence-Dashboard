# Power BI report

## Status

**Not built.** A `.pbix` is a binary Power BI Desktop artifact that cannot be generated or edited outside Power BI Desktop itself, so this repository does not claim to include one. Everything needed to build it is in this repository:

| Input | Where |
|---|---|
| Clean, modelled data | [`data/processed/fact_annual.csv`](../data/processed/fact_annual.csv), [`fact_quarterly.csv`](../data/processed/fact_quarterly.csv), [`dim_company.csv`](../data/processed/dim_company.csv) |
| Data model & relationships | [`docs/DATA_MODEL.md`](../docs/DATA_MODEL.md) + [`docs/data_model_diagram.svg`](../docs/data_model_diagram.svg) |
| Column definitions | [`docs/DATA_DICTIONARY.md`](../docs/DATA_DICTIONARY.md) |
| DAX measures (copy-paste ready) | [`docs/DAX_MEASURES.md`](../docs/DAX_MEASURES.md) |
| Page-by-page layout spec | [`docs/DASHBOARD_DESIGN.md`](../docs/DASHBOARD_DESIGN.md) + [`docs/dashboard_wireframe_page1.svg`](../docs/dashboard_wireframe_page1.svg) |

## Manual build steps (Power BI Desktop)

1. **Get Data → Text/CSV**, import all three files from `data/processed/`. Use **Import** mode (not DirectQuery).
2. In Power Query, set column types: `EndDate`/`FirstFYEndDate`/`LatestFYEndDate` → Date; boolean columns (`IsLatestFY`, `IsLatestQuarter`, `HasFullHistory4FY`) → True/False; text columns stay Text; everything else stays Decimal Number. No merges or transformations are needed here — they already happened in `python/data_validation.py`.
3. Add a Date table: **Modeling → New Table**:
   ```DAX
   Dim_Date = CALENDAR ( DATE(2012,1,1), DATE(2020,12,31) )
   ```
   then add `Year = YEAR('Dim_Date'[Date])`, `Quarter = "Q" & QUARTER('Dim_Date'[Date])`, `MonthNumber = MONTH('Dim_Date'[Date])`, `MonthName = FORMAT('Dim_Date'[Date], "MMM")` as calculated columns, and mark the table as a **Date Table** (right-click `Dim_Date` → Mark as date table → `Date` column).
4. **Build relationships** (Model view), all single-direction, matching [`docs/DATA_MODEL.md`](../docs/DATA_MODEL.md):
   - `Dim_Company[Stock]` (1) → `Fact_Annual[Stock]` (*)
   - `Dim_Company[Stock]` (1) → `Fact_Quarterly[Stock]` (*)
   - `Dim_Date[Date]` (1) → `Fact_Annual[EndDate]` (*)
   - `Dim_Date[Date]` (1) → `Fact_Quarterly[EndDate]` (*)
5. **Paste in the DAX measures** from [`docs/DAX_MEASURES.md`](../docs/DAX_MEASURES.md), organised into display folders: `Base`, `Ratios`, `Benchmarks`, `Ranking`, `Growth`.
6. **Format ratio columns/measures** as Percentage (2 decimal places) where noted `(%)`, and `DebtToEquity`/`AssetTurnover`/`CurrentRatio` as a plain decimal (`x` suffix in the visual title, not in the number format).
7. **Build the 4 pages** following [`docs/DASHBOARD_DESIGN.md`](../docs/DASHBOARD_DESIGN.md) — the layout tables give exact visual type, position and fields for each element.
8. **Page-level filter**: on Pages 1–3, add a page filter `Fact_Annual[IsLatestFY] = TRUE`. Page 4 has no such filter (it shows full company history).
9. **Drill-through**: on Page 4, enable it as a drill-through target on `Dim_Company[Stock]`; add a "Back" button (built-in drill-through back arrow is sufficient).
10. **Theme**: Import a single custom theme JSON (accent + neutral + one warning colour, per [`docs/DASHBOARD_DESIGN.md`](../docs/DASHBOARD_DESIGN.md) global rules) via **View → Themes → Browse for themes**.
11. **Export screenshots** of each finished page to `screenshots/executive_overview.png`, `industry_analysis.png` (Peer & Cohort Analysis), `financial_health.png`, `company_deep_dive.png` for the README.
12. Save as `powerbi/Public_Company_Financial_Intelligence.pbix` and commit it (the `.gitignore` in this repo only excludes Power BI's own cache/temp files, not the `.pbix` itself).

## Refresh

The data is a static 2012–2020 extract (see [`docs/DATASET_AUDIT.md`](../docs/DATASET_AUDIT.md)) — there is no live source to schedule a refresh against. To refresh with a newer extract of the same Kaggle dataset (if one is published), re-run `python python/data_validation.py` against the new raw files and use **Refresh** in Power BI Desktop; the model/measures do not need to change.
