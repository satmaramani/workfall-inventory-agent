# Inventory Agent

Inventory management service for product lifecycle, stock validation, and inventory queries.

## What This Service Does

- add and update products
- delete products
- list products and return product details
- validate stock availability for other agents
- reserve and release stock for invoice workflows
- prevent negative stock and invalid inventory transitions

## Default Port

`8001`

## Local Base URL

`http://localhost:8001`

## Depends On

- PostgreSQL on `5432`

## PostgreSQL Requirement

This service expects PostgreSQL to already be running before startup.

Recommended local database settings:

- host: `localhost`
- port: `5432`
- database: `workfall_multi_agent`
- user: `workfall`
- password: `workfall`

Tables and seed products are created automatically on startup. You do not need to manually create Inventory tables if the configured database is reachable and the user has permission to create tables.

## Tech Used Here

- FastAPI
- PostgreSQL via `psycopg`
- A2A-style request handling for stock operations

## Environment Setup

1. Copy the example file:

```powershell
copy .env.example .env
```

2. Update values if needed, especially:

- `DATABASE_URL`
- `A2A_SHARED_TOKEN`

Example:

```env
DATABASE_URL=postgresql://workfall:workfall@localhost:5432/workfall_multi_agent
```

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run Locally

```powershell
uvicorn app.main:app --reload --port 8001
```

## Key Endpoints

- `GET /api/v1/health`
- `GET /api/v1/capabilities`
- `GET /api/v1/products`
- `GET /api/v1/products/{product_id}`
- `POST /api/v1/products`
- `PATCH /api/v1/products/{product_id}/stock`
- `DELETE /api/v1/products/{product_id}`
- `POST /api/v1/a2a/request`

## Repo Structure

```text
inventory-agent/
  app/
    api/
    core/
    schemas/
    services/
  tests/
  .env.example
  requirements.txt
  .gitignore
  README.md
```

## Notes

- stock-changing operations use transactional reads and updates
- the `POST /api/v1/products` route supports same-`product_id` updates
- UI currently defaults to merging quantity when the same `product_id` is reused
