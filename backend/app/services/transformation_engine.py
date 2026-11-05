from datetime import datetime
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from backend.app.models.all_models import TransformationRun

EXCHANGE_RATES_TO_USD = {
    "USD": 1.0,
    "CAD": 0.74,
    "EUR": 1.08,
    "GBP": 1.28
}

class TransformationEngine:
    def __init__(self, db: Session):
        self.db = db

    def transform_orders(
        self, 
        workflow_run_id: str, 
        batch_id: str, 
        valid_records: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], TransformationRun]:
        """
        Normalizes valid order records:
        - Date normalization to datetime
        - Currency normalization to USD
        - Computes line item totals and discounts
        - Enriches store codes and catalog metadata
        """
        transformed_orders = []

        for rec in valid_records:
            order_id = rec.get("order_id") or rec.get("id")
            customer_id = rec.get("customer_id")
            store_id = str(rec.get("store_id", "STORE-DEFAULT")).strip().upper()
            currency = str(rec.get("currency", "USD")).strip().upper()
            rate = EXCHANGE_RATES_TO_USD.get(currency, 1.0)

            # Date normalization
            raw_date = rec.get("order_date")
            try:
                parsed_date = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
            except Exception:
                parsed_date = datetime.utcnow()

            # Handle items
            raw_items = rec.get("items")
            if raw_items is None and "quantity" in rec:
                raw_items = [{
                    "product_id": rec.get("product_id", "PROD-GENERIC"),
                    "sku": rec.get("sku", "SKU-GENERIC"),
                    "quantity": rec.get("quantity", 1),
                    "unit_price": rec.get("unit_price", 0.0),
                    "discount_pct": rec.get("discount_pct", 0.0)
                }]
            elif raw_items is None:
                raw_items = []

            normalized_items = []
            total_original_amount = 0.0

            for item in raw_items:
                qty = int(item.get("quantity", 1))
                price = float(item.get("unit_price", 0.0))
                disc = float(item.get("discount_pct", 0.0))
                line_total = round(qty * price * (1.0 - (disc / 100.0)), 2)
                total_original_amount += line_total

                normalized_items.append({
                    "product_id": str(item.get("product_id", "PROD-UNKNOWN")).strip(),
                    "sku": str(item.get("sku", "SKU-UNKNOWN")).strip(),
                    "quantity": qty,
                    "unit_price": price,
                    "discount_pct": disc,
                    "total_price": line_total
                })

            normalized_usd = round(total_original_amount * rate, 2)

            transformed_order = {
                "order_id": order_id,
                "customer_id": customer_id,
                "store_id": store_id,
                "order_date": parsed_date.isoformat(),
                "currency": currency,
                "original_amount": round(total_original_amount, 2),
                "normalized_usd_amount": normalized_usd,
                "item_count": len(normalized_items),
                "items": normalized_items,
                "status": "validated_and_transformed"
            }
            transformed_orders.append(transformed_order)

        t_run = TransformationRun(
            workflow_run_id=workflow_run_id,
            batch_id=batch_id,
            total_input=len(valid_records),
            total_transformed=len(transformed_orders),
            total_rejected=0,
            status="completed",
            executed_at=datetime.utcnow()
        )
        self.db.add(t_run)
        self.db.commit()
        self.db.refresh(t_run)

        return transformed_orders, t_run
