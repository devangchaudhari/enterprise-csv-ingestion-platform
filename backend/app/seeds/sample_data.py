import json
import csv
import os

SAMPLE_ORDERS = [
    {
        "order_id": "ORD-2026-1001",
        "customer_id": "CUST-9821",
        "store_id": "STORE-NYC-01",
        "order_date": "2026-10-24T14:30:00Z",
        "currency": "USD",
        "items": [
            {"product_id": "PROD-101", "sku": "ELEC-HEADPHONE-ANC", "quantity": 1, "unit_price": 199.99, "discount_pct": 0.0},
            {"product_id": "PROD-102", "sku": "ELEC-CABLE-USB-C", "quantity": 2, "unit_price": 14.99, "discount_pct": 10.0}
        ]
    },
    {
        "order_id": "ORD-2026-1002",
        "customer_id": "CUST-4412",
        "store_id": "STORE-LA-02",
        "order_date": "2026-10-24T15:10:00Z",
        "currency": "CAD",
        "items": [
            {"product_id": "PROD-201", "sku": "HOME-AIR-PURIFIER", "quantity": 1, "unit_price": 249.00, "discount_pct": 5.0}
        ]
    },
    {
        "order_id": "ORD-2026-1003",
        "customer_id": "CUST-8819",
        "store_id": "STORE-CHI-01",
        "order_date": "2026-10-24T16:00:00Z",
        "currency": "EUR",
        "items": [
            {"product_id": "PROD-301", "sku": "APP-WINTER-JACKET", "quantity": 1, "unit_price": 120.00, "discount_pct": 0.0},
            {"product_id": "PROD-302", "sku": "APP-THERMAL-GLOVES", "quantity": 2, "unit_price": 25.00, "discount_pct": 0.0}
        ]
    },
    {
        "order_id": "ORD-2026-1004",
        "customer_id": "CUST-1044",
        "store_id": "STORE-MIA-03",
        "order_date": "2026-10-24T16:45:00Z",
        "currency": "USD",
        "items": [
            {"product_id": "PROD-103", "sku": "ELEC-SMART-WATCH", "quantity": 1, "unit_price": 299.99, "discount_pct": 15.0}
        ]
    },
    {
        "order_id": "ORD-2026-1005",
        "customer_id": "CUST-3392",
        "store_id": "STORE-SEA-01",
        "order_date": "2026-10-24T17:15:00Z",
        "currency": "USD",
        "items": [
            {"product_id": "PROD-202", "sku": "HOME-COFFEE-MAKER", "quantity": 1, "unit_price": 89.50, "discount_pct": 0.0}
        ]
    },
    # Flawed records for data quality validation tests:
    {
        "order_id": "ORD-2026-ERR-01",
        "customer_id": "CUST-7741",
        "store_id": "STORE-NYC-01",
        "order_date": "2026-10-24T18:00:00Z",
        "currency": "USD",
        "items": [
            {"product_id": "PROD-101", "sku": "ELEC-HEADPHONE-ANC", "quantity": -2, "unit_price": 199.99, "discount_pct": 0.0}  # Negative qty!
        ]
    },
    {
        "order_id": "ORD-2026-ERR-02",
        "customer_id": "",  # Missing customer!
        "store_id": "STORE-LA-02",
        "order_date": "2026-10-24T18:30:00Z",
        "currency": "USD",
        "items": [
            {"product_id": "PROD-102", "sku": "ELEC-CABLE-USB-C", "quantity": 1, "unit_price": 14.99, "discount_pct": 0.0}
        ]
    },
    {
        "order_id": "ORD-2026-ERR-03",
        "customer_id": "CUST-9923",
        "store_id": "STORE-CHI-01",
        "order_date": "INVALID_DATE_FORMAT_HERE",  # Bad date!
        "currency": "USD",
        "items": [
            {"product_id": "PROD-201", "sku": "HOME-AIR-PURIFIER", "quantity": 1, "unit_price": 249.00, "discount_pct": 0.0}
        ]
    }
]

SAMPLE_PRODUCTS = [
    {"product_id": "PROD-101", "sku": "ELEC-HEADPHONE-ANC", "name": "Active Noise Cancelling Wireless Headphones", "category": "Electronics", "standard_cost": 85.00, "retail_price": 199.99},
    {"product_id": "PROD-102", "sku": "ELEC-CABLE-USB-C", "name": "Braided USB-C Charging Cable 2m", "category": "Electronics", "standard_cost": 3.20, "retail_price": 14.99},
    {"product_id": "PROD-103", "sku": "ELEC-SMART-WATCH", "name": "Titanium Fitness & GPS Smartwatch", "category": "Electronics", "standard_cost": 120.00, "retail_price": 299.99},
    {"product_id": "PROD-201", "sku": "HOME-AIR-PURIFIER", "name": "HEPA-13 Multi-Room Air Purifier", "category": "Home Goods", "standard_cost": 110.00, "retail_price": 249.00},
    {"product_id": "PROD-202", "sku": "HOME-COFFEE-MAKER", "name": "Precision Temperature Drip Coffee Maker", "category": "Home Goods", "standard_cost": 38.00, "retail_price": 89.50},
    {"product_id": "PROD-301", "sku": "APP-WINTER-JACKET", "name": "Insulated Thermal Parka Jacket", "category": "Apparel", "standard_cost": 45.00, "retail_price": 120.00},
    {"product_id": "PROD-302", "sku": "APP-THERMAL-GLOVES", "name": "Touchscreen Compatible Thermal Gloves", "category": "Apparel", "standard_cost": 7.50, "retail_price": 25.00}
]

SAMPLE_INVENTORY = [
    {"store_id": "STORE-NYC-01", "product_id": "PROD-101", "stock_on_hand": 140, "reserved_qty": 12, "reorder_point": 25},
    {"store_id": "STORE-NYC-01", "product_id": "PROD-102", "stock_on_hand": 550, "reserved_qty": 40, "reorder_point": 100},
    {"store_id": "STORE-LA-02", "product_id": "PROD-201", "stock_on_hand": 65, "reserved_qty": 8, "reorder_point": 20},
    {"store_id": "STORE-CHI-01", "product_id": "PROD-301", "stock_on_hand": 85, "reserved_qty": 15, "reorder_point": 30},
    {"store_id": "STORE-MIA-03", "product_id": "PROD-103", "stock_on_hand": 90, "reserved_qty": 5, "reorder_point": 15},
    {"store_id": "STORE-SEA-01", "product_id": "PROD-202", "stock_on_hand": 42, "reserved_qty": 4, "reorder_point": 10}
]

SAMPLE_SUPPLIERS = [
    {"supplier_id": "SUP-101", "name": "Apex Micro-Electronics Corp", "contact_email": "orders@apexmicro.com", "rating": 4.85, "fulfillment_sla_days": 2},
    {"supplier_id": "SUP-102", "name": "Nordic Clean Air Systems", "contact_email": "b2b@nordicclean.se", "rating": 4.92, "fulfillment_sla_days": 3},
    {"supplier_id": "SUP-103", "name": "Summit Outdoor Apparel Ltd", "contact_email": "wholesale@summitoutdoor.com", "rating": 4.70, "fulfillment_sla_days": 4}
]

def dump_sample_files(base_dir: str = "./data/samples"):
    os.makedirs(f"{base_dir}/sftp_root/incoming", exist_ok=True)
    os.makedirs(f"{base_dir}/sftp_root/archive", exist_ok=True)

    with open(f"{base_dir}/products.json", "w") as f:
        json.dump(SAMPLE_PRODUCTS, f, indent=2)

    with open(f"{base_dir}/inventory.json", "w") as f:
        json.dump(SAMPLE_INVENTORY, f, indent=2)

    with open(f"{base_dir}/suppliers.json", "w") as f:
        json.dump(SAMPLE_SUPPLIERS, f, indent=2)

    with open(f"{base_dir}/orders.json", "w") as f:
        json.dump(SAMPLE_ORDERS, f, indent=2)

    # Write CSV version of orders for SFTP/CSV connector
    csv_file = f"{base_dir}/sftp_root/incoming/daily_retail_orders_20261024.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["order_id", "customer_id", "store_id", "order_date", "currency", "product_id", "sku", "quantity", "unit_price", "discount_pct"])
        for order in SAMPLE_ORDERS:
            for item in order["items"]:
                writer.writerow([
                    order["order_id"],
                    order["customer_id"],
                    order["store_id"],
                    order["order_date"],
                    order["currency"],
                    item["product_id"],
                    item["sku"],
                    item["quantity"],
                    item["unit_price"],
                    item["discount_pct"]
                ])
