# Inventory Agent

Inventory service responsible for product lifecycle operations and stock validation.

## Responsibilities

- add, update, delete, and query inventory records
- validate stock availability
- provide product and quantity data to other services
- prevent invalid inventory transitions
- persist inventory records in PostgreSQL

## Default Port

`8001`

## Local Run Target

`http://localhost:8001`

## Planned Dependencies

- FastAPI
- Uvicorn
- Pydantic
- httpx
- SQLite or PostgreSQL later

## Run Locally

```bash
uvicorn app.main:app --reload --port 8001
```

## Key Endpoints

- `GET /api/v1/health`
- `GET /api/v1/capabilities`
- `GET /api/v1/products`
- `POST /api/v1/products`
- `PATCH /api/v1/products/{product_id}/stock`
- `POST /api/v1/a2a/request`

## Repo Layout

```text
inventory-agent/
  app/
    api/
    clients/
    core/
    models/
    schemas/
    services/
    agents/
    graphs/
  tests/
  .env.example
  requirements.txt
  .gitignore
  README.md
```
