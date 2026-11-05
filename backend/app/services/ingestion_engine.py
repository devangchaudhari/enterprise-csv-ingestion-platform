import hashlib
import json
from datetime import datetime
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from backend.app.models.all_models import IngestionBatch, SourceRecord, Pipeline

class IngestionEngine:
    def __init__(self, db: Session):
        self.db = db

    def create_batch(self, pipeline_id: str, workflow_run_id: str, source_type: str, checkpoint_val: str = None) -> IngestionBatch:
        batch_number = f"BATCH-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{pipeline_id[:8]}"
        batch = IngestionBatch(
            pipeline_id=pipeline_id,
            workflow_run_id=workflow_run_id,
            batch_number=batch_number,
            status="in_progress",
            total_records=0,
            source_type=source_type,
            checkpoint_val=checkpoint_val,
            started_at=datetime.utcnow()
        )
        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)
        return batch

    def ingest_records(self, batch_id: str, raw_records: List[Dict[str, Any]]) -> Tuple[int, int, List[str]]:
        """
        Idempotent ingestion:
        Computes SHA-256 checksum for each payload.
        Deduplicates against existing source records to prevent duplicate processing.
        Returns: (inserted_count, skipped_duplicates, record_ids)
        """
        batch = self.db.query(IngestionBatch).filter(IngestionBatch.id == batch_id).first()
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")

        inserted_count = 0
        skipped_count = 0
        inserted_ids = []

        for record in raw_records:
            # Deterministic JSON string for hashing
            serialized = json.dumps(record, sort_keys=True, default=str)
            checksum = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
            
            # Extract business key if available (e.g., order_id)
            business_key = (
                record.get("order_id") or 
                record.get("id") or 
                record.get("sku") or 
                record.get("transaction_id")
            )

            # Check if this exact checksum already exists in the system
            existing = self.db.query(SourceRecord).filter(SourceRecord.record_checksum == checksum).first()
            if existing:
                skipped_count += 1
                continue

            src_rec = SourceRecord(
                batch_id=batch_id,
                raw_payload=record,
                record_checksum=checksum,
                business_key=str(business_key) if business_key else None,
                ingested_at=datetime.utcnow()
            )
            self.db.add(src_rec)
            inserted_count += 1
            inserted_ids.append(src_rec.id)

        batch.total_records = inserted_count
        batch.status = "completed"
        batch.completed_at = datetime.utcnow()
        self.db.commit()

        return inserted_count, skipped_count, inserted_ids
