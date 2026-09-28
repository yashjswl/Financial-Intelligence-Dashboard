# Business Requirements

## Problem statement

An analyst covering a universe of ~4,400 public companies needs a fast way to size the universe, compare a company against its peers, and spot financially unusual companies — without sector or industry classifications, market data, or company names available. This project is a **financial intelligence and comparative-analysis solution built entirely from reported financial-statement data** (income statement, balance sheet, cash flow, 2012–2020, up to 4 fiscal years per company).

Because the dataset has no company name, sector, industry or geography (confirmed in [`DATASET_AUDIT.md`](DATASET_AUDIT.md)), peer comparison is reframed around **cohorts derived from the financials themselves**: a revenue-size band (Micro → Mega, quintiles of latest-FY revenue) and a profitability tier (Loss-making / Low / Moderate / High net margin). This is explicit and computed, not implied to be an industry classification.

## Who uses this

An analyst or student reviewing the company universe: sizing it, screening for financial outliers, and comparing one ticker against peers of similar size.

## Business questions the dashboard answers

### Executive (Page 1)
- How large is the company universe, and how many have usable financial data?
- What is the aggregate/median revenue and profitability across the universe?
- Which size band and profitability tier contribute the most revenue / highest margins?
- Which companies are the largest by revenue and by profitability?
- ~~Which sector contributes the most revenue~~ — not answerable (no sector field); replaced by size-band and profitability-tier breakdowns.

### Peer & cohort analysis (Page 2)
- How do revenue and profitability differ across size bands and profitability tiers?
- Where does a company sit versus companies of the same revenue size?
- Is a company's margin above or below the median of its size-band peers?
- Does a company combine strong revenue with weak profitability (revenue vs. margin scatter)?

### Financial health & outliers (Page 3)
- Which companies combine strong profitability with low leverage?
- Which companies have high liabilities relative to assets (Debt-to-Assets)?
- Which companies are statistical outliers on margin, leverage or turnover (3×IQR rule, documented in the audit)?
- How do profitability and company size interact?

### Company deep dive (Page 4)
- What is a selected company's financial profile (revenue, margins, leverage, cash flow) over its available fiscal years?
- How does it compare with the median of its own size-band / profitability-tier cohort?
- What is its year-over-year revenue and net-income growth?

## Explicitly out of scope (not supported by the data)

| Brief question | Status |
|---|---|
| Industry/sector revenue & profitability ranking | Not available — no industry field. Replaced with size-band / profitability-tier ranking. |
| Geographic breakdown | Not available — no country/region field. |
| Market capitalisation, share price, valuation multiples | Not available — no market-data field. |
| Revenue per employee | Not available — no headcount field. |
| Real-time or live figures | Not available — static extract, files dated 14 Jun 2020; the report will not claim to be live. |
| Multi-decade trend / CAGR | Not supported — at most 4 annual periods per company; YoY growth is valid, a long CAGR is not claimed. |

## Success criteria

1. Every KPI and visual traces to a field verified present in [`DATASET_AUDIT.md`](DATASET_AUDIT.md).
2. No fabricated company name, sector, geography or market data appears anywhere in the report or docs.
3. A recruiter or reviewer can tell, within 30 seconds of opening the README, what the dashboard does and what data backs it.
4. All comparisons ("above peer benchmark", "outlier") are explained with their exact calculation method.
