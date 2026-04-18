from __future__ import annotations

from decimal import Decimal
from typing import Any

import psycopg
from fastapi import HTTPException, status
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import DATABASE_URL, SERVICE_NAME
from app.core.utils import now_iso
from app.schemas.common import A2AContext


def get_connection() -> psycopg.Connection[Any]:
    try:
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    except psycopg.Error as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Inventory database unavailable: {exc}",
        ) from exc


def init_db() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS inventory_products (
                    product_id TEXT PRIMARY KEY,
                    product_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL CHECK (quantity >= 0),
                    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0),
                    category TEXT NOT NULL DEFAULT 'general',
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                INSERT INTO inventory_products (
                    product_id, product_name, quantity, unit_price, category, updated_at
                )
                VALUES
                    ('laptop-pro-15', 'Laptop Pro 15', 12, 1499.00, 'electronics', NOW()),
                    ('wireless-mouse', 'Wireless Mouse', 48, 29.00, 'accessories', NOW()),
                    ('noise-cancel-headphones', 'Noise Cancel Headphones', 25, 199.00, 'audio', NOW())
                ON CONFLICT (product_id) DO NOTHING
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_traces (
                    id BIGSERIAL PRIMARY KEY,
                    service_name TEXT NOT NULL,
                    session_id TEXT,
                    workflow_id TEXT,
                    trace_id TEXT,
                    step_name TEXT NOT NULL,
                    step_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    input_payload JSONB,
                    output_payload JSONB,
                    error_message TEXT,
                    model_name TEXT,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    total_tokens INTEGER,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        conn.commit()


def normalize_product(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "product_id": row["product_id"],
        "product_name": row["product_name"],
        "quantity": row["quantity"],
        "unit_price": float(row["unit_price"]) if isinstance(row["unit_price"], Decimal) else row["unit_price"],
        "category": row["category"],
    }


def fetch_product(cur: psycopg.Cursor[Any], product_id: str, for_update: bool = False) -> dict[str, Any]:
    sql = """
        SELECT product_id, product_name, quantity, unit_price, category
        FROM inventory_products
        WHERE product_id = %s
    """
    if for_update:
        sql += " FOR UPDATE"
    cur.execute(sql, (product_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return normalize_product(row)


def record_trace(
    *,
    context: A2AContext | None,
    step_name: str,
    step_type: str,
    status: str,
    input_payload: dict[str, Any] | None = None,
    output_payload: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO workflow_traces (
                    service_name, session_id, workflow_id, trace_id,
                    step_name, step_type, status, input_payload, output_payload, error_message
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    SERVICE_NAME,
                    context.session_id if context else None,
                    context.workflow_id if context else None,
                    context.trace_id if context else None,
                    step_name,
                    step_type,
                    status,
                    Jsonb(input_payload) if input_payload is not None else None,
                    Jsonb(output_payload) if output_payload is not None else None,
                    error_message,
                ),
            )
        conn.commit()
