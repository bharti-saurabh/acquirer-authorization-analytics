-- Retry Pattern Analysis — Optimal Retry Window by Decline Code
-- Straive Strategic Analytics | Acquirer Authorization Analytics

WITH initial_declines AS (
    SELECT
        a.txn_id,
        a.account_id,
        a.merchant_id,
        ROUND(a.amount, 0)                                   AS amount_rounded,
        a.response_code,
        a.auth_timestamp                                     AS decline_timestamp
    FROM fact_authorizations a
    WHERE a.response_code != '00'
      AND a.auth_timestamp BETWEEN :start_date AND :end_date
      AND a.response_code IN ('91','92','96','06','05','51')  -- retryable codes
),

retry_attempts AS (
    SELECT
        d.txn_id                                             AS original_txn_id,
        d.response_code                                      AS original_code,
        a2.txn_id                                            AS retry_txn_id,
        a2.response_code                                     AS retry_code,
        a2.auth_timestamp                                    AS retry_timestamp,
        DATEDIFF('second', d.decline_timestamp, a2.auth_timestamp) AS retry_delay_seconds,
        CASE WHEN a2.response_code = '00' THEN 1 ELSE 0 END AS retry_approved
    FROM initial_declines d
    JOIN fact_authorizations a2
        ON  a2.account_id  = d.account_id
        AND a2.merchant_id = d.merchant_id
        AND ROUND(a2.amount, 0) = d.amount_rounded
        AND a2.auth_timestamp > d.decline_timestamp
        AND a2.auth_timestamp <= d.decline_timestamp + INTERVAL '24 hours'
        AND a2.txn_id != d.txn_id
)

SELECT
    original_code,
    CASE
        WHEN retry_delay_seconds <= 300   THEN '0-5 min'
        WHEN retry_delay_seconds <= 1800  THEN '5-30 min'
        WHEN retry_delay_seconds <= 7200  THEN '30 min-2 hr'
        ELSE '2-24 hr'
    END                                                      AS retry_window,
    COUNT(*)                                                 AS retry_count,
    SUM(retry_approved)                                      AS approvals,
    SUM(retry_approved) * 1.0 / COUNT(*)                    AS retry_approval_rate
FROM retry_attempts
GROUP BY 1, 2
ORDER BY original_code, retry_window
