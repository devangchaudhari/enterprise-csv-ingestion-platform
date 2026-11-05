-- Mart Supplier Performance & SLA Analytics
SELECT
    supplier_id,
    supplier_name,
    ROUND(LEAST(100.0, rating * 20.0), 1) AS on_time_delivery_rate,
    ROUND(GREATEST(0.1, (5.0 - rating) * 0.8), 2) AS defect_rate_pct,
    ROUND(rating * 19.5, 1) AS overall_health_score,
    CURRENT_TIMESTAMP AS updated_at
FROM {{ ref('stg_suppliers') }}
