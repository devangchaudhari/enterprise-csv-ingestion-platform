-- Staging Suppliers Model
SELECT
    supplier_id,
    name AS supplier_name,
    contact_email,
    rating,
    fulfillment_sla_days
FROM {{ source('raw_retail', 'wh_suppliers') }}
