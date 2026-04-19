from __future__ import annotations

from pydantic import BaseModel, Field


class ProductUpsertRequest(BaseModel):
    product_id: str
    product_name: str
    quantity: int = Field(ge=0)
    unit_price: float = Field(ge=0)
    category: str = "general"
    merge_quantity: bool = False


class StockAdjustmentRequest(BaseModel):
    quantity_delta: int
