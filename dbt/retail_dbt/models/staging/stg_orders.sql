-- Staging Orders Model
SELECT
    order_id,
    customer_id,
    store_id,
    order_date,
    currency,
    original_amount,
    normalized_usd_amount,
    item_count,
    status,
    created_at
FROM {{ source('raw_retail', 'wh_orders') }}
