from __future__ import annotations

from app.core.db import fetch_product, get_connection, normalize_product


def list_products() -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT product_id, product_name, quantity, unit_price, category
                FROM inventory_products
                ORDER BY product_name ASC
                """
            )
            return {"products": [normalize_product(row) for row in cur.fetchall()]}


def get_product(product_id: str) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            return fetch_product(cur, product_id)


def upsert_product(product) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO inventory_products (
                    product_id, product_name, quantity, unit_price, category, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (product_id) DO UPDATE
                SET
                    product_name = EXCLUDED.product_name,
                    quantity = EXCLUDED.quantity,
                    unit_price = EXCLUDED.unit_price,
                    category = EXCLUDED.category,
                    updated_at = NOW()
                """,
                (
                    product.product_id,
                    product.product_name,
                    product.quantity,
                    product.unit_price,
                    product.category,
                ),
            )
            conn.commit()
            stored = fetch_product(cur, product.product_id)
    return {"status": "success", "product": stored, "message": "Product upserted successfully"}


def adjust_stock(product_id: str, quantity_delta: int) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            product = fetch_product(cur, product_id, for_update=True)
            new_quantity = product["quantity"] + quantity_delta
            if new_quantity < 0:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Quantity adjustment would result in negative stock",
                )
            cur.execute(
                """
                UPDATE inventory_products
                SET quantity = %s, updated_at = NOW()
                WHERE product_id = %s
                """,
                (new_quantity, product_id),
            )
            conn.commit()
            updated = fetch_product(cur, product_id)
    return {"status": "success", "product": updated, "message": "Stock updated successfully"}


def delete_product(product_id: str) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            product = fetch_product(cur, product_id)
            cur.execute("DELETE FROM inventory_products WHERE product_id = %s", (product_id,))
            conn.commit()
    return {"status": "success", "product": product, "message": "Product deleted successfully"}
