-- Mart Inventory Health & Stockout Monitoring
SELECT
    i.store_id,
    i.product_id,
    p.name AS product_name,
    CASE
        WHEN (i.stock_on_hand - i.reserved_qty) <= 0 THEN 'critical'
        WHEN (i.stock_on_hand - i.reserved_qty) < i.reorder_point THEN 'low'
        WHEN (i.stock_on_hand - i.reserved_qty) > 500 THEN 'surplus'
        ELSE 'optimal'
    END AS stock_level_status,
    (i.stock_on_hand - i.reserved_qty) AS available_stock,
    CASE 
        WHEN (i.stock_on_hand - i.reserved_qty) < i.reorder_point THEN TRUE 
        ELSE FALSE 
    END AS reorder_needed,
    CURRENT_TIMESTAMP AS updated_at
FROM {{ ref('stg_inventory') }} i
LEFT JOIN {{ ref('stg_products') }} p ON i.product_id = p.product_id
