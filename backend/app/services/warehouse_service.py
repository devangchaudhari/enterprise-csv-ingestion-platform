from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.all_models import WarehouseOrder, WarehouseOrderItem
from backend.app.core.config import settings

class WarehouseService:
    def __init__(self, db: Session):
        self.db = db

    def load_orders(self, orders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Loads normalized orders into the warehouse.
        Idempotent: updates existing order if present, otherwise inserts.
        """
        loaded_orders = 0
        loaded_items = 0

        for ord_data in orders:
            order_id = ord_data["order_id"]
            raw_dt = ord_data["order_date"]
            if isinstance(raw_dt, str):
                try:
                    dt_val = datetime.fromisoformat(raw_dt.replace("Z", "+00:00"))
                except Exception:
                    dt_val = datetime.utcnow()
            else:
                dt_val = raw_dt
            
            # Check if order already exists in warehouse
            existing_order = self.db.query(WarehouseOrder).filter(WarehouseOrder.order_id == order_id).first()
            if existing_order:
                existing_order.customer_id = ord_data["customer_id"]
                existing_order.store_id = ord_data["store_id"]
                existing_order.order_date = dt_val
                existing_order.currency = ord_data["currency"]
                existing_order.original_amount = ord_data["original_amount"]
                existing_order.normalized_usd_amount = ord_data["normalized_usd_amount"]
                existing_order.item_count = ord_data["item_count"]
                existing_order.status = "loaded"
                loaded_orders += 1
            else:
                wh_order = WarehouseOrder(
                    order_id=order_id,
                    customer_id=ord_data["customer_id"],
                    store_id=ord_data["store_id"],
                    order_date=dt_val,
                    currency=ord_data["currency"],
                    original_amount=ord_data["original_amount"],
                    normalized_usd_amount=ord_data["normalized_usd_amount"],
                    item_count=ord_data["item_count"],
                    status="loaded",
                    created_at=datetime.utcnow()
                )
                self.db.add(wh_order)
                loaded_orders += 1

            # Clean and reload order items for this order
            self.db.query(WarehouseOrderItem).filter(WarehouseOrderItem.order_id == order_id).delete()
            for item in ord_data.get("items", []):
                wh_item = WarehouseOrderItem(
                    order_id=order_id,
                    product_id=item["product_id"],
                    sku=item["sku"],
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    total_price=item["total_price"],
                    discount_pct=item.get("discount_pct", 0.0)
                )
                self.db.add(wh_item)
                loaded_items += 1

        self.db.commit()

        # If Snowflake credentials configured, mirror to Snowflake
        snowflake_status = "Skipped (no cloud credentials)"
        if settings.SNOWFLAKE_ACCOUNT and settings.SNOWFLAKE_USER and settings.SNOWFLAKE_PASSWORD:
            try:
                import snowflake.connector
                conn = snowflake.connector.connect(
                    user=settings.SNOWFLAKE_USER,
                    password=settings.SNOWFLAKE_PASSWORD,
                    account=settings.SNOWFLAKE_ACCOUNT,
                    warehouse=settings.SNOWFLAKE_WAREHOUSE,
                    database=settings.SNOWFLAKE_DATABASE,
                    schema=settings.SNOWFLAKE_SCHEMA
                )
                cursor = conn.cursor()
                # Run snowflake table creation if not exists & insert
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS WH_ORDERS (
                        ORDER_ID VARCHAR, CUSTOMER_ID VARCHAR, STORE_ID VARCHAR, 
                        ORDER_DATE TIMESTAMP, CURRENCY VARCHAR, NORMALIZED_USD_AMOUNT FLOAT
                    )
                """)
                for ord_data in orders:
                    cursor.execute("""
                        MERGE INTO WH_ORDERS t USING (SELECT %s as id, %s as cust, %s as store, %s as dt, %s as cur, %s as amt) s
                        ON t.ORDER_ID = s.id
                        WHEN MATCHED THEN UPDATE SET NORMALIZED_USD_AMOUNT = s.amt
                        WHEN NOT MATCHED THEN INSERT (ORDER_ID, CUSTOMER_ID, STORE_ID, ORDER_DATE, CURRENCY, NORMALIZED_USD_AMOUNT)
                        VALUES (s.id, s.cust, s.store, s.dt, s.cur, s.amt)
                    """, (ord_data["order_id"], ord_data["customer_id"], ord_data["store_id"], str(ord_data["order_date"]), ord_data["currency"], ord_data["normalized_usd_amount"]))
                conn.commit()
                cursor.close()
                conn.close()
                snowflake_status = f"Synced {len(orders)} orders to Snowflake DW ({settings.SNOWFLAKE_DATABASE})"
            except Exception as e:
                snowflake_status = f"Snowflake sync error: {str(e)}"

        return {
            "loaded_orders": loaded_orders,
            "loaded_items": loaded_items,
            "warehouse_destination": settings.WAREHOUSE_TYPE,
            "snowflake_sync": snowflake_status
        }
