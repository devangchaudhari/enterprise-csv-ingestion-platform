-- Mart Sales Summary
SELECT
    DATE(o.order_date) AS order_date,
    o.store_id,
    COALESCE(oi.category, 'General Merchandise') AS category,
    SUM(o.normalized_usd_amount) AS total_revenue_usd,
    COUNT(DISTINCT o.order_id) AS total_orders,
    ROUND(SUM(o.normalized_usd_amount) / NULLIF(COUNT(DISTINCT o.order_id), 0), 2) AS average_order_value,
    CURRENT_TIMESTAMP AS updated_at
FROM {{ ref('stg_orders') }} o
LEFT JOIN {{ ref('int_order_items') }} oi ON o.order_id = oi.order_id
GROUP BY 1, 2, 3
