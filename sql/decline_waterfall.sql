-- Authorization Decline Waterfall
-- Straive Strategic Analytics | Acquirer Authorization Analytics

WITH attempts AS (
    SELECT COUNT(*) AS total_attempts, SUM(amount) AS total_gmv
    FROM fact_authorizations
    WHERE auth_timestamp BETWEEN :start_date AND :end_date
),

by_outcome AS (
    SELECT
        CASE
            WHEN response_code = '00'                        THEN '1_Approved'
            WHEN response_code IN ('51','61','65')           THEN '2_Insufficient_Funds'
            WHEN response_code IN ('05','14','57','62','93') THEN '3_False_Decline'
            WHEN response_code IN ('41','43','54')           THEN '4_Card_Restriction'
            WHEN response_code IN ('55','75','06')           THEN '5_Velocity_Control'
            WHEN response_code IN ('91','92','96')           THEN '6_Technical'
            ELSE '7_Other'
        END                                                  AS decline_bucket,
        COUNT(*)                                             AS txn_count,
        SUM(amount)                                          AS gmv,
        SUM(CASE WHEN channel = 'CNP' THEN 1 ELSE 0 END)    AS cnp_count,
        SUM(CASE WHEN is_cross_border THEN 1 ELSE 0 END)     AS cross_border_count
    FROM fact_authorizations
    WHERE auth_timestamp BETWEEN :start_date AND :end_date
    GROUP BY 1
)

SELECT
    bo.decline_bucket,
    bo.txn_count,
    bo.gmv,
    bo.txn_count * 100.0 / a.total_attempts                  AS pct_of_total,
    bo.gmv / a.total_gmv * 100                               AS pct_gmv,
    bo.cnp_count * 1.0 / NULLIF(bo.txn_count, 0)            AS cnp_rate,
    bo.cross_border_count * 1.0 / NULLIF(bo.txn_count, 0)   AS cross_border_rate,
    SUM(bo.txn_count) OVER (ORDER BY bo.decline_bucket)      AS cumulative_count,
    SUM(bo.gmv) OVER (ORDER BY bo.decline_bucket)            AS cumulative_gmv
FROM by_outcome bo
CROSS JOIN attempts a
ORDER BY bo.decline_bucket
