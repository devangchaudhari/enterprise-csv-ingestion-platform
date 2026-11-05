from datetime import datetime
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from backend.app.models.all_models import DataQualityResult, RejectedRecord

class DataQualityEngine:
    def __init__(self, db: Session):
        self.db = db

    def validate_batch(
        self, 
        workflow_run_id: str, 
        batch_id: str, 
        records: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], DataQualityResult]:
        """
        Validates records against retail enterprise rules.
        Separates into valid records and rejected records.
        Records violations in rejected_records table and logs a DataQualityResult summary.
        """
        valid_records = []
        rejected_records = []
        rules_triggered_set = set()
        seen_order_ids = set()

        for rec in records:
            reasons = []
            order_id = rec.get("order_id") or rec.get("id")

            # 1. Required fields
            if not order_id:
                reasons.append(("REQUIRED_FIELD_MISSING", "Missing required field: order_id"))
            if not rec.get("customer_id"):
                reasons.append(("REQUIRED_FIELD_MISSING", "Missing required field: customer_id"))
            if not rec.get("store_id"):
                reasons.append(("REQUIRED_FIELD_MISSING", "Missing required field: store_id"))

            # 2. Duplicate business key in current batch
            if order_id:
                if order_id in seen_order_ids:
                    reasons.append(("DUPLICATE_BUSINESS_KEY", f"Duplicate order_id detected in batch: {order_id}"))
                else:
                    seen_order_ids.add(order_id)

            # 3. Date validation
            raw_date = rec.get("order_date")
            if not raw_date:
                reasons.append(("REQUIRED_FIELD_MISSING", "Missing order_date"))
            else:
                try:
                    # Try ISO parsing
                    datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
                except Exception:
                    reasons.append(("INVALID_DATE_FORMAT", f"Invalid date timestamp format: {raw_date}"))

            # 4. Currency validation
            currency = str(rec.get("currency", "USD")).upper()
            if currency not in ["USD", "CAD", "EUR", "GBP"]:
                reasons.append(("INVALID_CURRENCY", f"Unsupported currency code: {currency}"))

            # 5. Item validation (quantities and prices)
            items = rec.get("items")
            # If flat CSV record
            if items is None and "quantity" in rec:
                items = [{
                    "product_id": rec.get("product_id"),
                    "sku": rec.get("sku"),
                    "quantity": rec.get("quantity"),
                    "unit_price": rec.get("unit_price"),
                    "discount_pct": rec.get("discount_pct", 0)
                }]

            if items:
                for item in items:
                    try:
                        qty = float(item.get("quantity", 0))
                        if qty <= 0:
                            reasons.append(("NEGATIVE_OR_ZERO_QUANTITY", f"Quantity must be greater than zero. Found: {qty}"))
                    except (ValueError, TypeError):
                        reasons.append(("INVALID_NUMERIC_VALUE", f"Non-numeric quantity: {item.get('quantity')}"))

                    try:
                        price = float(item.get("unit_price", 0))
                        if price < 0:
                            reasons.append(("NEGATIVE_PRICE", f"Unit price cannot be negative: {price}"))
                    except (ValueError, TypeError):
                        reasons.append(("INVALID_NUMERIC_VALUE", f"Non-numeric unit price: {item.get('unit_price')}"))

            if reasons:
                for rule_code, msg in reasons:
                    rules_triggered_set.add(rule_code)
                    rej = RejectedRecord(
                        workflow_run_id=workflow_run_id,
                        batch_id=batch_id,
                        record_identifier=str(order_id) if order_id else "UNKNOWN",
                        raw_data=rec,
                        rejection_reason=msg,
                        rule_violated=rule_code,
                        created_at=datetime.utcnow()
                    )
                    self.db.add(rej)
                rejected_records.append(rec)
            else:
                valid_records.append(rec)

        reconciliation_status = "passed"
        if len(rejected_records) > 0:
            reconciliation_status = "warning" if len(valid_records) > 0 else "failed"

        dq_result = DataQualityResult(
            workflow_run_id=workflow_run_id,
            batch_id=batch_id,
            total_records=len(records),
            valid_records=len(valid_records),
            rejected_records=len(rejected_records),
            rules_triggered=list(rules_triggered_set),
            reconciliation_status=reconciliation_status,
            checked_at=datetime.utcnow()
        )
        self.db.add(dq_result)
        self.db.commit()
        self.db.refresh(dq_result)

        return valid_records, rejected_records, dq_result
