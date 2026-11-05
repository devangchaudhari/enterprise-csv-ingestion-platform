-- Staging Inventory Model
SELECT
    store_id,
    product_id,
    stock_on_hand,
    reserved_qty,
    reorder_point,
    (stock_on_hand - reserved_qty) AS available_qty,
    last_updated
FROM {{ source('raw_retail', 'wh_inventory') }}
