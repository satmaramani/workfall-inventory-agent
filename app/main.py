from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inventory has a small startup path: get the schema ready, then begin serving immediately.
    try:
        init_db()
        app.state.db_available = True
    except Exception:
        app.state.db_available = False
        raise
    yield


app = FastAPI(title="Inventory Agent", version="0.2.0", lifespan=lifespan)
app.state.db_available = False
app.include_router(router)
