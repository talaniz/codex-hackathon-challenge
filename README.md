# Codex Hackathon Challenge

An eCommerce demo built with FastAPI. Session 1 provides a public clothing storefront backed by SQLite, seeded automatically on first run.

## Requirements

- Python 3.12
- Dependencies from `requirements.txt` or `pyproject.toml`

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run The App

```bash
fastapi dev app/main.py
```

Open `http://127.0.0.1:8000/` to view the storefront. The app creates `codex_store.db` on first startup and seeds the product catalog automatically.

## Test

Run the Session 1 route smoke test:

```bash
pytest tests/test_routes_store.py -x
```

Run the inventory service tests:

```bash
pytest tests/test_services_inventory.py -x
```
