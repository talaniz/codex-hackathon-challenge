# Codex Hackathon Challenge

An eCommerce demo built with FastAPI to showcase Codex as a coding agent inside a running application.

The app includes a public clothing storefront, a protected admin backend for inventory management, and a rule engine for merchandising actions. Admins can describe inventory or merchandising rules in natural language, then the app uses the OpenAI Python SDK to ask Codex to generate a Python rule file and matching pytest test. Passing rules can be reviewed, activated, synced, and reflected on the storefront.

## Tech Stack

- Python 3.12
- FastAPI
- SQLAlchemy 2.x
- SQLite
- Jinja2 templates
- pytest
- httpx for route tests
- itsdangerous signed session cookies
- passlib with bcrypt for admin password hashing
- OpenAI Python SDK for Codex-powered rule generation

## Setup

Create and activate a virtual environment, then install dependencies:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Project metadata lives in `pyproject.toml`. The app creates `codex_store.db` automatically on first startup and seeds the product catalog and admin user.

## Environment Variables

Codex rule generation requires an OpenAI API key. Export your own key before using `/admin/rules/generate`:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

Optional development settings:

```bash
export OPENAI_CODEX_MODEL="gpt-5.1-codex-mini"
export DATABASE_URL="sqlite:///./codex_store.db"
export SECRET_KEY="replace-this-for-local-development"
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="codex-demo"
```

Do not commit real API keys, production secrets, or private credentials to the repository.

## Run The App

```bash
fastapi dev app/main.py
```

Open these URLs locally:

- Storefront: `http://127.0.0.1:8000/`
- Admin dashboard: `http://127.0.0.1:8000/admin`
- Admin login: `http://127.0.0.1:8000/admin/login`

Default development credentials:

- Username: `admin`
- Password: `codex-demo`

## Demo Workflow

1. Visit the storefront and browse the seeded clothing products.
2. Log in to the admin dashboard.
3. Manage inventory from `/admin/inventory`.
4. Open `/admin/rules` and generate a merchandising rule from natural language.
5. Review the generated rule file, test file, and Codex log output.
6. Activate the draft rule if generation and validation passed.
7. Click **Sync Now** to run active rules against current inventory.
8. Return to the storefront to confirm banners, low-stock badges, visibility changes, or discount tag effects.

## Rule Generation

Generated rules are written under `rules/`, and their tests are written under `tests/rules/`. A generated rule starts as an inactive draft. If its test passes and the rule validator accepts it, the admin can activate it from the rules page.

Rules are intentionally constrained:

- They must be pure and deterministic.
- They must not access the database, filesystem, environment, network, current time, or Codex.
- They may import only from `rules._base` and the Python standard library.
- They may return only supported action types: `TagSku`, `SetVisibility`, `ShowBanner`, and `SendNotification`.

If generation fails after the configured retry limit, the generated files are preserved as an inactive draft and the pytest or validation output is shown in the admin UI.

## Testing

Run focused tests for the area you changed:

```bash
pytest tests/test_routes_store.py -x
pytest tests/test_routes_admin.py -x
pytest tests/test_routes_rules.py -x
pytest tests/test_services_inventory.py -x
pytest tests/test_services_rule_engine.py -x
pytest tests/test_services_codex_client.py -x
pytest tests/rules/test_example_clearance.py -x -q
```

The project convention is to run targeted tests instead of the full suite unless a broader change requires it.

## Project Structure

```text
app/
  main.py                 FastAPI app factory and route registration
  config.py               Environment-backed settings
  db.py                   SQLAlchemy engine, sessions, and Base
  models.py               ORM models
  auth.py                 Admin auth, signed sessions, CSRF helpers
  routes/
    store.py              Public storefront routes
    admin.py              Admin dashboard, login, inventory CRUD
    rules.py              Rule generation, activation, sync endpoints
  services/
    inventory.py          Product seed and inventory operations
    rule_engine.py        Rule loading, validation, execution, dispatch
    codex_client.py       Codex prompt and generated rule workflow
  templates/              Jinja2 templates
rules/
  _base.py                Rule contract, action types, validator
  example_clearance.py    Hand-written reference rule
tests/
  rules/                  Rule-specific tests
static/                   CSS and product imagery
```
