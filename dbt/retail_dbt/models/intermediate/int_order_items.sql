-- Intermediate Order Items with Product Enrichment
WITH items AS (
    SELECT
        order_id,
        product_id,
        sku,
        quantity,
        unit_price,
        discount_pct,
        total_price
    FROM {{ source('raw_retail', 'wh_order_items') }}
),
products AS (
    SELECT
        product_id,
        name AS product_name,
        category,
        standard_cost
    FROM {{ ref('stg_products') }}
)
SELECT
    i.order_id,
    i.product_id,
    i.sku,
    p.product_name,
    p.category,
    i.quantity,
    i.unit_price,
    i.discount_pct,
    i.total_price,
    (i.quantity * p.standard_cost) AS total_cost,
    (i.total_price - (i.quantity * p.standard_cost)) AS gross_margin
FROM items i
LEFT JOIN products p ON i.product_id = p.product_id
