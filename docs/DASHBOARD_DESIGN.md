# Dashboard Design (as built)

Four pages in the Power BI service, built on the model in [`DATA_MODEL.md`](DATA_MODEL.md) with the measures in [`DAX_MEASURES.md`](DAX_MEASURES.md). Screenshots: [`../screenshots/`](../screenshots/).

## Design rules applied

- **Plain chart types only**: bars, columns, lines, scatter, tables, matrix and cards; no 3D, gauges or pie charts. The default Power BI palette is used (no custom theme).
- **Money cards use display units** (T / bn / M) rather than raw digits, and percentage measures are formatted as percentages.
- **Axes that hide data are disclosed on the chart**: clipped scatter axes say so in the subtitle; log scales are used for revenue and balance-sheet totals that span six orders of magnitude.
- **Company-level visuals use `dim_company[Stock]`**, so peer-benchmark measures can read the company's size band from the dimension (see [`DAX_MEASURES.md`](DAX_MEASURES.md) §3).
- **A footnote on every page** states the basis (latest fiscal year per company; source; static data).

## Page 1: Executive Overview
*Filters: `IsLatestFY = True`.*

| Visual | Content |
|---|---|
| 6 KPI cards | Total Companies, Total Revenue, Total Net Income, Median Revenue, Profit Margin %, EBITDA (approx.) |
| Revenue by Size Band | Bar chart, `RevenueSizeBand` × Total Revenue |
| Net Margin by Size Band | Bar chart, weighted (`Profit Margin %`) and median (`Median Company Net Margin %`) per band |
| Top 10 Companies by Revenue | Table, Top N by Total Revenue |
| Top 10 by Net Margin | Table, Top N by Profit Margin % (dominated by revenue-light entities; see [`KEY_INSIGHTS.md`](KEY_INSIGHTS.md)) |
| Slicers | `ProfitabilityTier`, `DataCompletenessFlag`, `RevenueSizeBand` (dropdowns) |

**Questions answered:** how large is the universe; what are aggregate and median revenue and profitability; which size cohorts carry the revenue and the margin; who are the largest companies.

## Page 2: Peer & Cohort Analysis
*Filters: `IsLatestFY = True`.*

| Visual | Content |
|---|---|
| Revenue vs Net Margin | Scatter, one dot per company; X = Total Revenue (log), Y = Profit Margin % clipped to ±100%, size = Total Assets, colour = size band |
| Companies by Size Band and Profitability Tier | Matrix of company counts (grand total 4,422) |
| Peer Comparison | Table: company margin, `Peer Median Net Margin %` (median of its size band), and the variance |
| Slicers | Same three as Page 1 |

**Questions answered:** how profitability varies across size cohorts; how many companies sit in each cohort; whether a company is above or below the median margin of same-size peers.

## Page 3: Financial Health & Outliers
*Filters: `IsLatestFY = True`, `DataCompletenessFlag = Analysis-ready` (4,140 companies).*

| Visual | Content |
|---|---|
| Rule text | Outlier = net margin below −81.1% or above +89.7% (3×IQR fences; see [`DAX_MEASURES.md`](DAX_MEASURES.md) §4b) |
| Profitability vs Leverage | Scatter; X = total liabilities ÷ total assets (clipped to 0–300%), Y = net margin (clipped to ±100%) |
| Liabilities vs Assets | Scatter on log–log axes; points above the diagonal have liabilities greater than assets |
| High-margin, low-leverage screen | Table filtered to net margin ≥ 16.4% and liabilities ÷ assets ≤ 39.2% (282 companies) and non-blank leverage |
| Net margin outliers | Table filtered to margins outside the fences (595 companies) |
| Slicers | `ProfitabilityTier`, `RevenueSizeBand` |

**Questions answered:** which companies combine high margins with low leverage; which carry liabilities above assets; which margins are statistically unusual, and by what rule.

## Page 4: Company Deep Dive
*Filters: none at page level (full history); the KPI cards and the peer-benchmark cards carry a visual-level `IsLatestFY = True`.*

| Visual | Content |
|---|---|
| Company selector | Single-select dropdown on `dim_company[Stock]` |
| Company profile | Size band, profitability tier, data-completeness flag |
| 5 KPI cards | Total Revenue, Profit Margin %, Return on Equity %, Revenue Growth YoY %, Debt to Assets % |
| Revenue and net income over time | Columns (revenue) + line (net income), fiscal years |
| Margins over time | Gross, operating and net margin lines |
| Quarterly revenue | Columns over the last four quarters (`fact_quarterly`) |
| Company vs peer benchmark | Company margin and leverage against the size-band median, with variance |

**Questions answered:** how one company's size, margins, returns and leverage evolve over its available years, and how it compares with same-size peers.

## Not built

Drill-through from the company tables to Page 4 (the company slicer is used instead, because a drill-through filter and a slicer on the same field conflict), a ranking visual, and a custom report theme.
