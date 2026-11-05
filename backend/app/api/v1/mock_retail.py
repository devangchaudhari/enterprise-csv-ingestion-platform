import time
from typing import Dict, Any, List
from fastapi import APIRouter, Header, HTTPException, Query, Body, Response
from backend.app.seeds.sample_data import (
    SAMPLE_ORDERS, SAMPLE_INVENTORY, SAMPLE_PRODUCTS, SAMPLE_SUPPLIERS
)

router = APIRouter(prefix="/mock-retail", tags=["Mock Retail Enterprise API"])

# Tracks simulation state for retry testing
FAILURE_SIMULATION_STATE = {"attempts_seen": 0}

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "MockRetailEnterpriseCoreAPI",
        "version": "2026.4.0",
        "timestamp": time.time()
    }

@router.get("/orders")
def get_orders(
    limit: int = 50,
    checkpoint: str = None
):
    orders = SAMPLE_ORDERS[:limit]
    return {
        "total": len(orders),
        "checkpoint": f"chk-{time.time()}",
        "orders": orders
    }

@router.get("/inventory")
def get_inventory():
    return {"total": len(SAMPLE_INVENTORY), "inventory": SAMPLE_INVENTORY}

@router.get("/products")
def get_products():
    return {"total": len(SAMPLE_PRODUCTS), "products": SAMPLE_PRODUCTS}

@router.get("/suppliers")
def get_suppliers():
    return {"total": len(SAMPLE_SUPPLIERS), "suppliers": SAMPLE_SUPPLIERS}

@router.post("/downstream-orders")
def receive_downstream_orders(
    payload: Dict[str, Any] = Body(...),
    x_api_key: str = Header(None, alias="X-API-Key"),
    x_idempotency_key: str = Header(None, alias="X-Idempotency-Key"),
    x_simulate_failure: str = Header(None, alias="X-Simulate-Failure")
):
    """
    Downstream Partner ERP Delivery Endpoint:
    Receives reconciled orders, records idempotency key,
    and supports failure simulation for testing retries.
    """
    if x_simulate_failure == "api_error":
        FAILURE_SIMULATION_STATE["attempts_seen"] += 1
        # Fail the first attempt with a 500 server error, then succeed on retry!
        if FAILURE_SIMULATION_STATE["attempts_seen"] == 1:
            raise HTTPException(
                status_code=500,
                detail="Simulated Downstream Partner Gateway Timeout / Internal 500 error"
            )
        else:
            # Succeeded on retry
            FAILURE_SIMULATION_STATE["attempts_seen"] = 0
            return {
                "status": "accepted_on_retry",
                "message": "Processed successfully after retry",
                "idempotency_key": x_idempotency_key,
                "order_count": payload.get("order_count", 0)
            }

    return {
        "status": "delivered",
        "message": "Orders successfully posted to downstream partner system",
        "idempotency_key": x_idempotency_key,
        "order_count": payload.get("order_count", 0)
    }
