# Key Insights

All figures below were computed by running the queries in this document against `data/processed/fact_annual.csv` and `data/processed/dim_company.csv` (the same tables the Power BI report loads), using each company's **latest available fiscal year**. Every insight is labelled as an **observed fact** (read straight from the data), a **calculated metric** (a defined formula applied to the data), or an **interpretation** (a judgement call about what the numbers might mean) — interpretations are opinions to sanity-check, not facts.

## Universe

- **Observed fact:** the dataset covers 4,422 unique tickers, with 4,140 (93.6%) having positive revenue and positive total assets in their latest fiscal year (`DataCompletenessFlag = Analysis-ready`); the remaining 282 have zero/negative revenue or assets in their latest period and are excluded from ratio-based analysis.
- **Observed fact:** 4,279 companies (96.8%) have all 4 annual fiscal periods available; 143 have fewer.

## Revenue concentration by size cohort

- **Calculated metric:** grouping companies into revenue-size quintiles (`RevenueSizeBand`, computed on latest-FY revenue), the top quintile ("5 - Mega," 836 companies) accounts for **$16.40 trillion** of the **$18.41 trillion** total latest-FY revenue in the dataset — **89.0%** of aggregate revenue from 19% of companies.
- **Interpretation:** revenue in this universe is heavily concentrated in a small number of very large companies, which is expected for a cross-section of *all* public companies (most listed companies are small by revenue even though a few dominate aggregate totals) rather than a dataset artifact.

## Profitability by size cohort

- **Calculated metric:** revenue-weighted net margin (aggregate net income ÷ aggregate revenue) by size band: Mega 8.51%, Large 6.92%, Small 4.81%, Mid 4.68%, Micro −45.72% (Micro band skewed by loss-making pre-revenue companies).
- **Calculated metric:** the *median* company's net margin by band (less sensitive to a few very large or very negative numbers) is highest for Mega-band companies (6.78%) and lowest for Micro-band companies (−45.72%), with Large/Small/Mid clustered between 4.6% and 5.5%.
- **Interpretation:** both the aggregate and the typical-company view agree that larger companies in this dataset are, on average, more profitable and more consistently profitable than the smallest companies — plausibly because the Micro band contains a disproportionate share of early-stage/loss-making, pre-revenue companies (biotech, small-cap developers) rather than because size itself drives margin.
- **Calculated metric:** the correlation between log-revenue and net margin (companies with positive revenue) is **+0.20** — a weak positive relationship, not a strong one. Size explains only a small part of the variation in profitability.

## Largest companies (latest fiscal year, by revenue)

- **Observed fact:** the ten largest companies by latest-FY revenue are WMT ($524.0B), AMZN ($280.5B), BP ($276.9B), AAPL ($260.2B), CVS ($255.8B), XOM ($255.6B), UNH ($242.2B), MCK ($231.1B), T ($181.2B) and ABC ($179.6B).
- **Observed fact:** among these, AAPL has by far the highest net margin (21.2%), while MCK and ABC — both very large by revenue — have net margins under 0.5%, illustrating that revenue rank and profitability rank are not the same ranking.

## Highest-margin companies are small, revenue-light investment vehicles

- **Observed fact:** the companies with the single highest net margins in the dataset (ASG 4,528%, ASA 3,856%, EOS 2,577%, RVT 1,757%, …) all have very small `TotalRevenue` (roughly $0.8M–$22M) alongside much larger `NetIncome`.
- **Interpretation:** this pattern (tiny revenue line, large net income) is typical of closed-end investment funds/trusts, where "revenue" in this field captures a small fee/interest line while net income includes investment gains — not evidence of an unusually well-run operating business, and not an error in the data. The dashboard's outlier view flags these but does not label them "bad" or "best-run," consistent with the project's outlier-transparency requirement.
- **Calculated metric:** 604 of 4,181 companies with positive revenue (14.4%) fall outside 3×IQR fences on net margin — confirming the audit's finding that net margin is a heavy-tailed metric in this dataset, primarily because of small-denominator effects like the one above.

## Leverage

- **Calculated metric:** median Debt-to-Assets (`TotalLiabilities / TotalAssets`) across companies with a computable ratio is **57.4%**; the middle 50% of companies (IQR) sits between 36.9% and 78.4%.
- **Observed fact:** the eight companies with the highest Debt-to-Assets ratios (up to 72.6× for SONN) all have total assets under $6M — the ratio is extreme because the denominator is very small, not because liabilities are unusually large in absolute terms. This is flagged as a scale effect, not treated as "worst-financed."

## Companies combining high profitability with low leverage

- **Calculated metric:** defining "high profitability" as net margin at or above the analysis-ready universe's 75th percentile (≥16.4%) and "low leverage" as Debt-to-Assets at or below the 25th percentile (≤39.2%), **284 of 4,140** analysis-ready companies (6.9%) meet both criteria in their latest fiscal year. The top of this list overlaps heavily with the small-revenue investment vehicles noted above (ASG, ASA, EOS, RVT, GF, USA, GAM, CLM), for the same tiny-denominator reason.
- **Interpretation:** as a *screening* rule this combination is useful, but any shortlist drawn from it should be reviewed for the revenue-scale effect described above before being read as "financially strongest."

## Growth

- **Calculated metric:** median year-over-year revenue growth (latest fiscal year vs. each company's own prior available period, computed via `FYIndex`) across the 12,339 company-years where a prior period exists is **+4.8%**.
- **Observed fact:** the fastest revenue growth in the latest available year belongs to VERB (+283%), GWGH (+238%), APG (+221%), CPRX (+204%) and SLGL (+177%) — all growing from a comparatively small prior-year revenue base, which mechanically produces large percentage swings.

## What this dashboard does **not** claim

- No industry, sector or geographic pattern is reported — the source data does not contain those fields (see [`DATASET_AUDIT.md`](DATASET_AUDIT.md)).
- No claim is made about companies not present in the dataset (survivorship: only tickers with reported 2012–2020 filings are included).
- No real-time or post-2020 statement is made; the underlying files are dated 14 Jun 2020.
