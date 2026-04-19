from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

SERVICE_NAME = os.getenv("SERVICE_NAME", "inventory-agent")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8001"))
A2A_SHARED_TOKEN = os.getenv("A2A_SHARED_TOKEN", "")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://workfall:workfall@localhost:5432/workfall_multi_agent",
)
