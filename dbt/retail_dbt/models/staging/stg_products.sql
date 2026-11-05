-- Staging Products Model
SELECT
    product_id,
    sku,
    name,
    category,
    standard_cost,
    retail_price
FROM {{ source('raw_retail', 'wh_products') }}
