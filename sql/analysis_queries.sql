-- Reference SQL for the star schema described in docs/DATA_MODEL.md.
--
-- No SQL database is part of this project — the pipeline is flat CSV files
-- (data/processed/*.csv) loaded straight into Power BI. These queries are
-- provided as portable reference logic: the same calculations as
-- docs/DAX_MEASURES.md, expressed in ANSI SQL, in case the processed tables
-- are ever loaded into a real database (Postgres/SQL Server/SQLite all run
-- these with only minor syntax changes, noted inline).
--
-- Assumed schema (matches docs/DATA_DICTIONARY.md exactly):
--   fact_annual(Stock, EndDate, FYIndex, IsLatestFY, TotalRevenue, NetIncome,
--               GrossProfit, OperatingIncome, EBIT, TotalAssets,
--               TotalLiabilities, TotalEquity, Depreciation, ...)
--   dim_company(Stock, RevenueSizeBand, ProfitabilityTier, DataCompletenessFlag, ...)

-- ---------------------------------------------------------------------
-- 1. Universe size and data-quality split (Page 1 KPI cards)
-- ---------------------------------------------------------------------
SELECT
    COUNT(DISTINCT Stock)                                            AS total_companies,
    SUM(CASE WHEN DataCompletenessFlag = 'Analysis-ready' THEN 1 ELSE 0 END) AS analysis_ready_companies
FROM dim_company;

-- ---------------------------------------------------------------------
-- 2. Executive KPIs, latest fiscal year only
-- ---------------------------------------------------------------------
SELECT
    SUM(TotalRevenue)                                   AS total_revenue,
    SUM(NetIncome)                                       AS total_net_income,
    CASE WHEN SUM(TotalRevenue) > 0
         THEN SUM(NetIncome) * 1.0 / SUM(TotalRevenue)
         ELSE NULL END                                    AS profit_margin_pct,
    SUM(EBIT) + SUM(Depreciation)                          AS ebitda_approx
FROM fact_annual
WHERE IsLatestFY = 1;  -- SQLite/Postgres boolean literal; use IsLatestFY = TRUE on stricter engines

-- ---------------------------------------------------------------------
-- 3. Revenue and profitability by size cohort (Page 1/2)
-- ---------------------------------------------------------------------
SELECT
    d.RevenueSizeBand,
    COUNT(DISTINCT f.Stock)                              AS companies,
    SUM(f.TotalRevenue)                                   AS total_revenue,
    CASE WHEN SUM(f.TotalRevenue) > 0
         THEN SUM(f.NetIncome) * 1.0 / SUM(f.TotalRevenue)
         ELSE NULL END                                     AS weighted_net_margin
FROM fact_annual f
JOIN dim_company d ON d.Stock = f.Stock
WHERE f.IsLatestFY = 1
GROUP BY d.RevenueSizeBand
ORDER BY total_revenue DESC;

-- ---------------------------------------------------------------------
-- 4. Top 10 companies by revenue (Page 1 table)
-- ---------------------------------------------------------------------
SELECT Stock, TotalRevenue, NetIncome,
       CASE WHEN TotalRevenue > 0 THEN NetIncome * 1.0 / TotalRevenue ELSE NULL END AS net_margin
FROM fact_annual
WHERE IsLatestFY = 1
ORDER BY TotalRevenue DESC
LIMIT 10;

-- ---------------------------------------------------------------------
-- 5. Peer (cohort) median net margin, used as the benchmark in
--    docs/DAX_MEASURES.md "Peer Median Net Margin %"
-- ---------------------------------------------------------------------
-- Median-by-group needs a window function; shown for Postgres/SQLite (3.25+).
WITH margins AS (
    SELECT
        f.Stock,
        d.RevenueSizeBand,
        CASE WHEN f.TotalRevenue > 0 THEN f.NetIncome * 1.0 / f.TotalRevenue ELSE NULL END AS net_margin
    FROM fact_annual f
    JOIN dim_company d ON d.Stock = f.Stock
    WHERE f.IsLatestFY = 1
)
SELECT
    RevenueSizeBand,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY net_margin) AS peer_median_net_margin
FROM margins
WHERE net_margin IS NOT NULL
GROUP BY RevenueSizeBand;

-- ---------------------------------------------------------------------
-- 6. Company vs. peer-cohort variance (Page 2/4)
-- ---------------------------------------------------------------------
WITH margins AS (
    SELECT
        f.Stock,
        d.RevenueSizeBand,
        CASE WHEN f.TotalRevenue > 0 THEN f.NetIncome * 1.0 / f.TotalRevenue ELSE NULL END AS net_margin
    FROM fact_annual f
    JOIN dim_company d ON d.Stock = f.Stock
    WHERE f.IsLatestFY = 1
),
peer_median AS (
    SELECT RevenueSizeBand, PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY net_margin) AS peer_median_net_margin
    FROM margins WHERE net_margin IS NOT NULL GROUP BY RevenueSizeBand
)
SELECT
    m.Stock, m.RevenueSizeBand, m.net_margin, p.peer_median_net_margin,
    m.net_margin - p.peer_median_net_margin AS variance_pts
FROM margins m
JOIN peer_median p ON p.RevenueSizeBand = m.RevenueSizeBand
WHERE m.net_margin IS NOT NULL
ORDER BY variance_pts DESC;

-- ---------------------------------------------------------------------
-- 7. Financial-health screen: high margin + low leverage
--    (mirrors docs/KEY_INSIGHTS.md methodology — P75 margin, P25 leverage)
-- ---------------------------------------------------------------------
WITH ratios AS (
    SELECT
        f.Stock,
        CASE WHEN f.TotalRevenue > 0 THEN f.NetIncome * 1.0 / f.TotalRevenue ELSE NULL END AS net_margin,
        CASE WHEN f.TotalAssets > 0 THEN f.TotalLiabilities * 1.0 / f.TotalAssets ELSE NULL END AS debt_to_assets
    FROM fact_annual f
    JOIN dim_company d ON d.Stock = f.Stock
    WHERE f.IsLatestFY = 1 AND d.DataCompletenessFlag = 'Analysis-ready'
),
thresholds AS (
    SELECT
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY net_margin)      AS margin_p75,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY debt_to_assets)  AS leverage_p25
    FROM ratios
)
SELECT r.*
FROM ratios r, thresholds t
WHERE r.net_margin >= t.margin_p75
  AND r.debt_to_assets <= t.leverage_p25
ORDER BY r.net_margin DESC;

-- ---------------------------------------------------------------------
-- 8. Year-over-year revenue growth (uses FYIndex, not calendar date —
--    see docs/DATA_MODEL.md for why fiscal-index joins are used instead
--    of calendar time-intelligence)
-- ---------------------------------------------------------------------
SELECT
    cur.Stock, cur.EndDate, cur.TotalRevenue, prev.TotalRevenue AS prior_fy_revenue,
    CASE WHEN prev.TotalRevenue <> 0
         THEN (cur.TotalRevenue - prev.TotalRevenue) * 1.0 / ABS(prev.TotalRevenue)
         ELSE NULL END AS revenue_growth_yoy
FROM fact_annual cur
LEFT JOIN fact_annual prev
       ON prev.Stock = cur.Stock AND prev.FYIndex = cur.FYIndex - 1
WHERE cur.IsLatestFY = 1
ORDER BY revenue_growth_yoy DESC;
