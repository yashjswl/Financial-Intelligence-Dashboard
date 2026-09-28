# Data Dictionary

Produced by [`python/data_validation.py`](../python/data_validation.py) from the raw files in `data/raw/` (see [`DATASET_AUDIT.md`](DATASET_AUDIT.md) for the raw-file audit). All three processed tables are loaded into Power BI as-is; no further column changes happen in Power Query beyond type-setting and the model relationships described in [`DATA_MODEL.md`](DATA_MODEL.md).

## `fact_annual.csv` — grain: one row per (Stock, EndDate), annual filings, 17,511 rows

| Column | Type | Raw or derived | Meaning | Transformation |
|---|---|---|---|---|
| Stock | text | raw (`stock`) | Ticker symbol, the only company identifier in the source | none |
| EndDate | date | raw (`endDate`) | Fiscal period end date | parsed to date |
| FYIndex | integer | derived | 1 = company's earliest available annual period, increases by 1 per period | rank of EndDate within Stock |
| IsLatestFY | boolean | derived | True for each company's most recent available annual period | FYIndex == max(FYIndex) per Stock |
| PeriodsAvailable | integer | derived | Count of annual periods available for this company (1–4) | max(FYIndex) per Stock |
| TotalRevenue | number | raw (`totalRevenue`) | Total revenue | none |
| CostOfRevenue | number | raw (`costOfRevenue`) | Cost of revenue | none |
| GrossProfit | number | raw (`grossProfit`) | Revenue − cost of revenue | none |
| TotalOperatingExpenses | number | raw (`totalOperatingExpenses`) | Total operating expenses | none |
| OperatingIncome | number | raw (`operatingIncome`) | Revenue − operating expenses | none |
| EBIT | number | raw (`ebit`) | Earnings before interest & tax (differs from OperatingIncome in ~11% of rows per audit) | none |
| SGA | number | raw (`sellingGeneralAdministrative`) | SG&A expense | none |
| ResearchDevelopment | number | raw (`researchDevelopment`) | R&D expense; 66% missing (not all companies report R&D) | none |
| InterestExpense | number | raw (`interestExpense`) | Interest expense, source stores as negative; 25% missing | none |
| IncomeTaxExpense | number | raw (`incomeTaxExpense`) | Income tax expense | none |
| IncomeBeforeTax | number | raw (`incomeBeforeTax`) | Pre-tax income | none |
| NetIncome | number | raw (`netIncome`) | Net income | none |
| TotalAssets | number | raw (`totalAssets`) | Total assets | none |
| TotalLiabilities | number | raw (`totalLiab`) | Total liabilities | none |
| TotalEquity | number | raw (`totalStockholderEquity`) | Total stockholders' equity; negative in 1,410 rows (audit #4) | none |
| TotalCurrentAssets | number | raw (`totalCurrentAssets`) | Current assets | none |
| TotalCurrentLiabilities | number | raw (`totalCurrentLiabilities`) | Current liabilities | none |
| Cash | number | raw (`cash`) | Cash and equivalents | none |
| Inventory | number | raw (`inventory`) | Inventory; 45% missing | none |
| NetReceivables | number | raw (`netReceivables`) | Net receivables | none |
| LongTermDebt | number | raw (`longTermDebt`) | Long-term debt; 36% missing — blank is "not reported", not "zero" | none |
| ShortTermDebt | number | raw (`shortLongTermDebt`) | Current portion of long-term debt; 69% missing | none |
| Goodwill | number | raw (`goodWill`) | Goodwill; 45% missing | none |
| RetainedEarnings | number | raw (`retainedEarnings`) | Retained earnings | none |
| CashFromOperations | number | raw (`totalCashFromOperatingActivities`) | Operating cash flow | none |
| CapEx | number | derived (`-capitalExpenditures`) | Capital expenditure, sign-flipped to a positive outflow amount | negated |
| Depreciation | number | raw (`depreciation`) | Depreciation & amortisation | none |
| DividendsPaid | number | raw (`dividendsPaid`) | Dividends paid, negative = cash out; 52% missing | none |
| StockRepurchases | number | raw (`repurchaseOfStock`) | Share buybacks, negative = cash out; 40% missing | none |
| FreeCashFlow | number | derived | CashFromOperations − CapEx | `CFO + capitalExpenditures` (source CapEx already negative) |
| FreeCashFlowMargin | number (%) | derived | FreeCashFlow ÷ TotalRevenue | DIVIDE-safe, blank if revenue ≤ 0 |
| GrossMargin | number (%) | derived | GrossProfit ÷ TotalRevenue | DIVIDE-safe |
| OperatingMargin | number (%) | derived | OperatingIncome ÷ TotalRevenue | DIVIDE-safe |
| NetMargin | number (%) | derived | NetIncome ÷ TotalRevenue | DIVIDE-safe |
| EffectiveTaxRate | number (%) | derived | IncomeTaxExpense ÷ IncomeBeforeTax | DIVIDE-safe |
| ReturnOnAssets | number (%) | derived | NetIncome ÷ TotalAssets | DIVIDE-safe |
| ReturnOnEquity | number (%) | derived | NetIncome ÷ TotalEquity | **blank when TotalEquity ≤ 0** (1,410 rows; audit #4) |
| AssetTurnover | number (x) | derived | TotalRevenue ÷ TotalAssets | DIVIDE-safe |
| CurrentRatio | number (x) | derived | TotalCurrentAssets ÷ TotalCurrentLiabilities | DIVIDE-safe |
| DebtToAssets | number (%) | derived | TotalLiabilities ÷ TotalAssets | DIVIDE-safe |
| DebtToEquity | number (x) | derived | TotalLiabilities ÷ TotalEquity | blank when TotalEquity ≤ 0 |
| RevenueGrowthYoY | number (%) | derived | (Revenue − prior-FY Revenue) ÷ \|prior-FY Revenue\| | joined on Stock + FYIndex−1; blank for each company's first available period (5,172 rows) |
| NetIncomeGrowthYoY | number (%) | derived | (NetIncome − prior-FY NetIncome) ÷ \|prior-FY NetIncome\| | same join |

**Used in dashboard:** all columns (Pages 1–4).

## `fact_quarterly.csv` — grain: one row per (Stock, EndDate), quarterly filings, 17,651 rows

Same construction as `fact_annual`, restricted to the columns needed for a quarterly trend on the Company Deep Dive page: `Stock, EndDate, QIndex, IsLatestQuarter, PeriodsAvailable, TotalRevenue, GrossProfit, OperatingIncome, NetIncome, TotalAssets, TotalEquity, CashFromOperations, CapEx, FreeCashFlow, GrossMargin, OperatingMargin, NetMargin, RevenueGrowthYoQ, NetIncomeGrowthYoQ`. Definitions mirror the annual table; `RevenueGrowthYoQ`/`NetIncomeGrowthYoQ` compare each quarter to the prior available quarter (QIndex−1), i.e. **quarter-over-quarter**, not year-over-year (the source has no consistent 4-quarters-back alignment for every company).

**Used in dashboard:** Page 4 (Company Deep Dive) quarterly trend visual only.

## `dim_company.csv` — grain: one row per Stock, 4,422 rows

| Column | Type | Raw or derived | Meaning |
|---|---|---|---|
| Stock | text | raw | Ticker (primary key) |
| FirstFYEndDate | date | derived | Earliest annual EndDate available |
| LatestFYEndDate | date | derived | Most recent annual EndDate available |
| PeriodsAvailableAnnual | integer | derived | Count of annual periods (1–4) |
| HasFullHistory4FY | boolean | derived | True if all 4 annual periods are present |
| LatestFYRevenue | number | derived | TotalRevenue at the company's latest annual period |
| LatestFYNetIncome | number | derived | NetIncome at the latest annual period |
| LatestFYTotalAssets | number | derived | TotalAssets at the latest annual period |
| LatestFYNetMargin | number (%) | derived | NetMargin at the latest annual period |
| RevenueSizeBand | text | derived | Quintile of LatestFYRevenue among companies with revenue > 0: `1 - Micro` … `5 - Mega`; `Not meaningful (revenue <= 0)` for the 241 companies with zero/negative latest-FY revenue |
| ProfitabilityTier | text | derived | `Loss-making (<=0%)` / `Low (0-5%)` / `Moderate (5-15%)` / `High (>15%)` based on LatestFYNetMargin; `Not meaningful (revenue <= 0)` where margin is undefined |
| DataCompletenessFlag | text | derived | `Analysis-ready` if latest-FY revenue > 0 and total assets > 0, else `Limited (zero/negative revenue or assets)` (282 companies) |

**Used in dashboard:** slicers and cohort grouping on all pages; RevenueSizeBand and ProfitabilityTier stand in for the industry/sector dimension the source data does not contain (see [`BUSINESS_REQUIREMENTS.md`](BUSINESS_REQUIREMENTS.md)).

## Not carried into the model

Columns present in the raw files but excluded because they are >65% missing, not used by any KPI, or redundant (see [`DATASET_AUDIT.md`](DATASET_AUDIT.md) §4): `deferredLongTermAssetCharges`, `deferredLongTermLiab`, `otherStockholderEquity`, `otherLiab`, `otherAssets`, `otherCurrentAssets`, `otherCurrentLiab`, `treasuryStock`, `capitalSurplus`, `intangibleAssets`, `shortTermInvestments`, `minorityInterest`, `discontinuedOperations`, `otherOperatingExpenses`, `netIncomeApplicableToCommonShares`, `netIncomeFromContinuingOps`, `totalOtherIncomeExpenseNet`, `changeTo*` cash-flow reconciliation lines, `effectOfExchangeRate`, `netBorrowings`, `issuanceOfStock`, `investments`, `otherCashflowsFrom*`.
