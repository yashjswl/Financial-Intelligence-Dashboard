# Dashboard Design Specification

4 pages, 1280×720 canvas (standard 16:9 Power BI page). Layout coordinates are (x, y, width, height) in px, given so the pages can be built directly in Power BI Desktop without guesswork.

## Global design rules

- **Theme:** one accent colour for KPI cards/positive values, one neutral grey for structure, one warning colour reserved for outlier/negative flags — applied via a single Power BI theme JSON, not ad hoc per visual.
- **Typography:** Segoe UI throughout; page titles 20pt semibold, section titles 12pt semibold, body/labels 9–10pt. No more than 2 font sizes per visual.
- **KPI cards:** value + label + (where applicable) a one-line qualifier ("latest FY", "analysis-ready companies only") — never an unlabelled number.
- **Color use:** color encodes one dimension per chart (e.g. RevenueSizeBand) and is never the only way a value is distinguished — every colored series also has a label/legend or is sorted so rank is readable without color.
- **Slicers:** grouped in a single left-hand or top strip per page, consistent position across all 4 pages; a "Reset filters" bookmark button on each page.
- **Every page filters `Fact_Annual[IsLatestFY] = TRUE`** except Page 4, which removes that filter to show a company's full history (see [`DAX_MEASURES.md`](DAX_MEASURES.md) filter-context convention).
- **Tooltips:** every visual gets a report-page tooltip or default tooltip showing the exact metric name and underlying value, not just a rounded chart label.
- **No 3D, no gauge, no pie-with->6-slices** — this is a data-density-appropriate exec dashboard, not a decoration exercise.

---

## Page 1 — Executive Overview

**Answers:** How large is the company universe? What is aggregate/median revenue and profitability? Which cohorts and companies are largest / most profitable?

| Element | Type | Position (x,y,w,h) | Measure(s) / fields |
|---|---|---|---|
| Page title + as-of note | Text | 0,0,1280,40 | "Executive Overview — latest fiscal year per company" |
| Companies | KPI card | 20,50,190,100 | `[Total Companies]` |
| Total Revenue | KPI card | 220,50,190,100 | `[Total Revenue]` |
| Total Net Income | KPI card | 420,50,190,100 | `[Total Net Income]` |
| Profit Margin % | KPI card | 620,50,190,100 | `[Profit Margin %]` |
| EBITDA (approx.) | KPI card | 820,50,190,100 | `[EBITDA (approx.)]` (footnote: "approximate — EBIT + Depreciation") |
| Median Revenue | KPI card | 1020,50,240,100 | `[Median Revenue]` |
| Revenue by Size Band | Clustered bar | 20,170,610,230 | `Dim_Company[RevenueSizeBand]` × `[Total Revenue]` |
| Net Margin by Size Band | Clustered bar | 650,170,610,230 | `Dim_Company[RevenueSizeBand]` × `[Profit Margin %]` (revenue-weighted) and `[Median Company Net Margin %]` (two series) |
| Top 10 Companies by Revenue | Table | 20,420,610,270 | `Stock`, `TotalRevenue`, `NetIncome`, `Profit Margin %`, ranked by `[Revenue Rank (Universe)]` |
| Top 10 Companies by Net Margin | Table | 650,420,610,270 | `Stock`, `TotalRevenue`, `Profit Margin %` — filtered `TotalRevenue > 0`, ranked by `[Net Margin Rank (Universe)]` |
| Slicers (left strip) | Slicer panel | integrated above visuals | `RevenueSizeBand`, `ProfitabilityTier`, `DataCompletenessFlag` |

**Interactions:** clicking a size-band bar cross-filters both tables; a "Analysis-ready only" toggle (bookmark) applies `DataCompletenessFlag = Analysis-ready`.

---

## Page 2 — Peer & Cohort Analysis

**Answers:** How do revenue-size and profitability cohorts differ financially? Where does a company sit versus same-size peers? Does a company have strong revenue but weak profitability?

| Element | Type | Position | Measure(s) / fields |
|---|---|---|---|
| Page title | Text | 0,0,1280,40 | "Peer & Cohort Analysis" |
| Size-band slicer | Slicer | 20,50,230,110 | `RevenueSizeBand` |
| Profitability-tier slicer | Slicer | 20,170,230,110 | `ProfitabilityTier` |
| Revenue vs. Profit Margin scatter | Scatter | 270,50,520,340 | X = `[Total Revenue]` (log axis), Y = `[Profit Margin %]`, size = `[Total Assets]`, legend = `RevenueSizeBand`, one point per company |
| Cohort Revenue Ranking | Bar (sorted) | 810,50,450,160 | `RevenueSizeBand` × `[Total Revenue]`, descending |
| Cohort Margin Ranking | Bar (sorted) | 810,220,450,170 | `RevenueSizeBand` × `[Median Company Net Margin %]`, descending |
| Peer Comparison Table | Table + conditional formatting | 270,410,990,280 | `Stock`, `RevenueSizeBand`, `Profit Margin %`, `[Peer Median Net Margin %]`, `[Company Net Margin % vs Peer Median]` (data bars / red-green on the variance column only) |
| Distribution of companies by cohort | Stacked bar or matrix | 20,300,230,390 | `RevenueSizeBand` × `ProfitabilityTier`, count of companies |

**Interactions:** selecting a point on the scatter filters the Peer Comparison Table to that company plus its cohort; cohort bars cross-filter the scatter.

---

## Page 3 — Financial Health & Outliers

**Answers:** Which companies combine strong profitability with low leverage? Which have high liabilities relative to assets? Which are statistical outliers, and on what basis?

| Element | Type | Position | Measure(s) / fields |
|---|---|---|---|
| Page title | Text | 0,0,1280,40 | "Financial Health & Outliers" |
| Methodology note | Text box | 20,45,1240,30 | "Outlier = beyond 3×IQR (interquartile range) fences on the metric shown, computed on analysis-ready companies. An outlier is not automatically 'weak' — see docs/KEY_INSIGHTS.md." |
| Profitability vs Leverage scatter | Scatter | 20,90,610,320 | X = `[Debt to Assets %]`, Y = `[Profit Margin %]`, size = `[Total Revenue]`, legend = `RevenueSizeBand`; quadrant reference lines at cohort medians |
| Liabilities vs Assets scatter | Scatter | 650,90,610,320 | X = `[Total Assets]` (log), Y = `[Total Liabilities]` (log), 45° reference line = Liabilities==Assets |
| High-Margin / Low-Leverage Screen | Table | 20,430,610,260 | `Stock`, `Profit Margin %`, `[Debt to Assets %]` — filtered to margin ≥ P75 and leverage ≤ P25 (matches [`KEY_INSIGHTS.md`](KEY_INSIGHTS.md) methodology), with a footnote flagging that small-revenue investment vehicles cluster here |
| Outlier Table (Net Margin) | Table + conditional formatting | 650,430,610,260 | `Stock`, `TotalRevenue`, `Profit Margin %`, an `Is Outlier (Net Margin)` flag column, sorted by \|margin\| descending |

**Outlier flag (conceptual DAX, computed as a measure using `VAR`):**
```DAX
Is Outlier (Net Margin) =
VAR Q1 = PERCENTILEX.INC ( ALLSELECTED ( Fact_Annual[Stock] ), [Profit Margin %], 0.25 )
VAR Q3 = PERCENTILEX.INC ( ALLSELECTED ( Fact_Annual[Stock] ), [Profit Margin %], 0.75 )
VAR IQR = Q3 - Q1
VAR Val = [Profit Margin %]
RETURN
    IF ( NOT ISBLANK ( Val ) && ( Val < Q1 - 3 * IQR || Val > Q3 + 3 * IQR ), "Outlier", "Typical" )
```

---

## Page 4 — Company Deep Dive

**Answers:** What is a selected company's financial profile over time? How does it compare with its cohort? What is its growth trajectory?

| Element | Type | Position | Measure(s) / fields |
|---|---|---|---|
| Company selector | Slicer (single-select, searchable) | 20,10,300,40 | `Dim_Company[Stock]` |
| Company header | Text/card | 340,10,940,40 | Selected `Stock`, `RevenueSizeBand`, `ProfitabilityTier` (via a concatenated measure) |
| Latest FY Revenue | KPI card | 20,60,235,90 | `[Total Revenue]` filtered `IsLatestFY` |
| Latest FY Net Margin | KPI card | 265,60,235,90 | `[Profit Margin %]` filtered `IsLatestFY` |
| Latest FY ROE | KPI card | 510,60,235,90 | `[Return on Equity %]` filtered `IsLatestFY` (shows "n/a — negative equity" when blank) |
| Revenue YoY Growth | KPI card | 755,60,235,90 | `[Revenue Growth YoY %]` filtered `IsLatestFY` |
| Debt to Assets % | KPI card | 1000,60,260,90 | `[Debt to Assets %]` filtered `IsLatestFY` |
| Revenue & Net Income trend (annual) | Combo chart (bar+line) | 20,160,620,260 | X = `EndDate` (all `FYIndex`, filter removed), bars = `TotalRevenue`, line = `NetIncome` |
| Margin trend (annual) | Line chart | 650,160,610,260 | X = `EndDate`, lines = `GrossMargin`, `OperatingMargin`, `NetMargin` |
| Quarterly revenue trend | Line/area chart | 20,430,610,260 | `Fact_Quarterly[EndDate]` × `TotalRevenue`, filtered to the selected `Stock` |
| Company vs Peer Benchmark | Table | 650,430,610,260 | Metric name, Company value, `[Peer Median Net Margin %]` / peer median debt-to-assets, variance — reuses Page 2/3 benchmark measures |

**Drill-through:** right-click any company in Pages 1–3 tables → "Drill through to Company Deep Dive," carrying the `Stock` filter — implemented as a standard Power BI drill-through page target on Page 4.

---

## Page-to-question traceability (Phase 9 requirement)

| Page | Business questions answered |
|---|---|
| 1. Executive Overview | Universe size, aggregate/median revenue & profitability, largest companies, cohort contribution to revenue |
| 2. Peer & Cohort Analysis | Cohort-level differences, revenue-vs-profitability relationship, peer benchmarking |
| 3. Financial Health & Outliers | Profitability-vs-leverage screening, liabilities-vs-assets check, statistically unusual companies |
| 4. Company Deep Dive | Single-company trajectory, quarterly trend, benchmark variance |

## Wireframe

A layout wireframe for Page 1 (Executive Overview) is provided as [`dashboard_wireframe_page1.svg`](dashboard_wireframe_page1.svg) to illustrate the grid above; Pages 2–4 follow the same left-slicer / top-KPI grid pattern described in their tables.
