from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from app.core.config import DATABASE_URL, SERVICE_NAME, SERVICE_PORT
from app.core.security import require_agent_token, require_api_token
from app.core.utils import now_iso
from app.core.db import fetch_product, get_connection, normalize_product, record_trace
from app.schemas.common import A2AError, A2AMeta, A2ARequest, A2AResponse
from app.schemas.inventory import ProductUpsertRequest, StockAdjustmentRequest
from app.services.inventory_service import adjust_stock, delete_product, get_product, list_products, upsert_product


router = APIRouter(prefix="/api/v1")


@router.get("/health")
def health() -> dict:
    from app.main import app
    db_available = app.state.db_available

    return {
        "status": "ok" if db_available else "degraded",
        "service": SERVICE_NAME,
        "port": SERVICE_PORT,
        "database_url": DATABASE_URL.rsplit("@", 1)[-1],
        "db_available": db_available,
        "timestamp": now_iso(),
    }


@router.get("/capabilities")
def capabilities() -> dict:
    return {
        "service": SERVICE_NAME,
        "intents": ["check_stock", "reserve_stock", "release_stock", "add_product", "update_product", "delete_product", "list_products"],
    }


@router.get("/products")
def products(x_api_token: str | None = Header(default=None)) -> dict:
    require_api_token(x_api_token)
    return list_products()


@router.get("/products/{product_id}")
def product(product_id: str, x_api_token: str | None = Header(default=None)) -> dict:
    require_api_token(x_api_token)
    return get_product(product_id)


@router.post("/products")
def create_or_update_product(product: ProductUpsertRequest, x_api_token: str | None = Header(default=None)) -> dict:
    require_api_token(x_api_token)
    return upsert_product(product)


@router.patch("/products/{product_id}/stock")
def patch_stock(product_id: str, request: StockAdjustmentRequest, x_api_token: str | None = Header(default=None)) -> dict:
    require_api_token(x_api_token)
    return adjust_stock(product_id, request.quantity_delta)


@router.delete("/products/{product_id}")
def remove_product(product_id: str, x_api_token: str | None = Header(default=None)) -> dict:
    require_api_token(x_api_token)
    return delete_product(product_id)


@router.post("/a2a/request", response_model=A2AResponse)
def a2a_request(request: A2ARequest, x_agent_token: str | None = Header(default=None)) -> A2AResponse:
    require_agent_token(x_agent_token)
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                if request.intent == "check_stock":
                    product_id = request.payload["product_id"]
                    quantity = int(request.payload.get("quantity", 1))
                    product = fetch_product(cur, product_id)
                    available = product["quantity"] >= quantity
                    result = {
                        "product": product,
                        "requested_quantity": quantity,
                        "available_quantity": product["quantity"],
                        "is_available": available,
                    }
                elif request.intent == "reserve_stock":
                    product_id = request.payload["product_id"]
                    quantity = int(request.payload.get("quantity", 1))
                    product = fetch_product(cur, product_id, for_update=True)
                    if product["quantity"] < quantity:
                        raise HTTPException(status_code=409, detail="Requested quantity exceeds available stock")
                    cur.execute(
                        "UPDATE inventory_products SET quantity = quantity - %s, updated_at = NOW() WHERE product_id = %s",
                        (quantity, product_id),
                    )
                    conn.commit()
                    updated = fetch_product(cur, product_id)
                    result = {
                        "product": updated,
                        "reserved_quantity": quantity,
                        "remaining_quantity": updated["quantity"],
                    }
                elif request.intent == "release_stock":
                    product_id = request.payload["product_id"]
                    quantity = int(request.payload.get("quantity", 1))
                    fetch_product(cur, product_id, for_update=True)
                    cur.execute(
                        "UPDATE inventory_products SET quantity = quantity + %s, updated_at = NOW() WHERE product_id = %s",
                        (quantity, product_id),
                    )
                    conn.commit()
                    updated = fetch_product(cur, product_id)
                    result = {
                        "product": updated,
                        "released_quantity": quantity,
                        "current_quantity": updated["quantity"],
                    }
                elif request.intent == "list_products":
                    cur.execute(
                        "SELECT product_id, product_name, quantity, unit_price, category FROM inventory_products ORDER BY product_name ASC"
                    )
                    result = {"products": [normalize_product(row) for row in cur.fetchall()]}
                else:
                    raise HTTPException(status_code=404, detail="Unsupported inventory intent")

        record_trace(
            context=request.context,
            step_name=f"inventory_{request.intent}",
            step_type="a2a_handler",
            status="success",
            input_payload=request.model_dump(),
            output_payload=result,
        )
        return A2AResponse(
            request_id=request.request_id,
            status="success",
            agent="inventory",
            result=result,
            error=None,
            meta=A2AMeta(retry_count=0, timestamp=now_iso(), source_service=SERVICE_NAME, target_service="caller"),
        )
    except HTTPException as exc:
        record_trace(
            context=request.context,
            step_name=f"inventory_{request.intent}",
            step_type="a2a_handler",
            status="failed",
            input_payload=request.model_dump(),
            error_message=str(exc.detail),
        )
        return A2AResponse(
            request_id=request.request_id,
            status="failed",
            agent="inventory",
            result=None,
            error=A2AError(code="INVENTORY_ERROR", message=str(exc.detail), retriable=exc.status_code >= 500),
            meta=A2AMeta(retry_count=0, timestamp=now_iso(), source_service=SERVICE_NAME, target_service="caller"),
        )
