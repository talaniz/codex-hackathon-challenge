# codex-hackathon-challenge

## Overview
An eCommerce demo built to showcase Codex as a coding agent inside a
running application. There is a small public storefront for clothing,
and an admin backend for managing inventory. The differentiating
feature: admins describe inventory and merchandising rules in natural 
language; the app invokes Codex via the Python SDK, Codex writes a 
Python rule file and a pytest test for it under `rules/`, runs the 
test until it passes, and the new rule is loaded by the rule engine 
on the next sync.

## Stack and idioms (pinned, do not change without asking)
- Python 3.12
- fastapi[standard] == 0.136.1  (this includes uvicorn, jinja2,
  python-multipart, httpx — do not install these separately)
- sqlalchemy == 2.0.49  (use 2.x style only: DeclarativeBase, Mapped,
  mapped_column, select(); no legacy Column() on models, no
  Query.filter)
- jinja2 == 3.1.6  (templates extend a single base.html)
- pytest == 8.x
- itsdangerous == 2.2.0  (signed session cookies)
- passlib[bcrypt] == 1.7.4
- httpx == 0.28.1  (test client; use AsyncClient, not TestClient)
- openai  (OpenAI Python SDK — used in app/services/codex_client.py 
  to invoke Codex programmatically for rule generation; version pinned 
  by the local Codex CLI install — do not hand-pin)

Use Annotated[...] with Depends() for FastAPI dependencies.
Use PEP 604 unions (X | None).

Project metadata lives in `pyproject.toml` only. Do not create
`setup.cfg` or `setup.py`.

Do not introduce new dependencies, frameworks, or tooling not on this
list without asking first. You may *propose* new dependencies in your
response — explain what and why — but do not install them or modify
`pyproject.toml` until I confirm.

## Directory layout
    app/
      __init__.py
      main.py                 # FastAPI app factory, route registration
      config.py               # settings, env loading
      db.py                   # engine, session, Base
      models.py               # SQLAlchemy ORM classes only
      auth.py                 # session cookie auth, password hashing
      services/
        inventory.py          # inventory sync logic
        rule_engine.py        # rule loader, executor, action dispatcher
        codex_client.py       # Codex SDK invocation, prompt template
      routes/
        store.py              # public storefront
        admin.py              # admin dashboard, inventory CRUD
        rules.py              # rule generation + activation endpoints
      templates/              # jinja2 templates, base.html + pages/
      static/                 # CSS, minimal JS
    rules/
      __init__.py
      _base.py                # Rule, InventorySnapshot, Action types, validator
      example_clearance.py    # one hand-written rule, used as Codex's reference
    tests/
      conftest.py
      test_routes_store.py
      test_routes_admin.py
      test_services_inventory.py
      test_services_rule_engine.py
      rules/
        test_example_clearance.py
    AGENTS.md
    rules/AGENTS.md           # nested file with rule contract — read it
    requirements.txt
    pyproject.toml

## Filesystem scope
- During build sessions: may scaffold and modify anything under `app/` 
  and `tests/`, except existing files under `tests/rules/`, which must 
  not be modified once created.
- For rule generation (session 4 and beyond): may ONLY create new files
  in `rules/` and `tests/rules/`. Must not modify `rules/_base.py`,
  `rules/example_clearance.py`, `rules/__init__.py`, or any existing
  rule file.
- Never modify this AGENTS.md or `rules/AGENTS.md` without being asked.

### File naming
Generated rule names must be lowercase snake_case and derived from the admin-provided rule title or description. Do not overwrite existing rule or test files. If a name already exists, append `_2`, `_3`, etc.

## Code conventions
- ORM classes live in `app/models.py`. No business logic there.
- Business logic lives in `app/services/`. Routes call services;
  services call models.
- Route handlers in `app/routes/` are thin: validate input, call a
  service, render a template or return JSON.
- Auth: server-side sessions via `itsdangerous.URLSafeTimedSerializer`
  in an HTTP-only, SameSite=Lax cookie. Passwords hashed with
  passlib[bcrypt]. No JWT, no OAuth, no third-party auth libraries.
- CSRF: hand-rolled, signed token stored in the session and rendered
  as a hidden form field. No new dependencies.
- Templates extend `base.html`. No inline styles; use static CSS.

## Testing
- After changes to a module, run only the corresponding tests:
  `pytest tests/<matching_path> -x`. Do not run the full suite unless
  explicitly asked.
- Every new service function gets at least one positive and one
  negative test.
- Use `httpx.AsyncClient` with the FastAPI app for route tests.

## Rule generation contract (session 4 and beyond)

Generated rules are subject to stricter constraints than the rest of
the codebase. These apply to any file Codex creates in `rules/` or
`tests/rules/` during rule generation.

### Purity
Generated rules must be pure and deterministic. They must not:
- access the database directly
- make network calls
- read environment variables
- read or write files
- call Codex (no recursion)
- use `random` without a seeded `random.Random` instance
- depend on the current time except via `datetime` values passed in
  through the `InventorySnapshot`
- generated tests may import only from `rules._base`, the generated rule file, and the Python standard library unless existing project test helpers are required.

### Imports
Generated rules may only import from:
- `rules._base` (for `Rule`, `InventorySnapshot`, `Sku`, and the
  Action types)
- the Python standard library — `datetime`, `typing`, and similar
  modules are expected and fine

No third-party imports. The rule loader runs a static AST check on
every rule file and rejects (quarantines) any file that violates this.

### Action types (closed set)
Rules return `list[Action]` where each Action is one of:
- `TagSku(sku: str, tag: str)`
- `SetVisibility(sku: str, state: Literal["visible", "low_stock_badge", "hidden"])`
- `ShowBanner(text: str, severity: Literal["info", "warning"])`
- `SendNotification(channel: Literal["admin"], text: str)`

If the rule's intent cannot be expressed within these Action types and
the purity constraints, create no files and explain why in the final
response.

### Test execution
After creating a rule and its test, run only:

    pytest tests/rules/test_<snake_name>.py -x -q

Iterate on failures until the test passes. Do not run any other tests.

### Dependencies
Codex may not install dependencies during rule generation. The import
constraint above makes this redundant, but to be explicit: no
`pip install`, no edits to `pyproject.toml`, no new third-party
packages.

## When to stop and ask
- If a requirement here is ambiguous, stop and ask before guessing.
- If a session's acceptance criteria seem unreachable within the file
  structure, stop and ask.
- If you find yourself wanting to modify a file in a "do not modify"
  list, stop and ask.
- If the work would require a new dependency, stop and ask.
- Do not silently work around constraints.

## Out of scope (do not build, do not suggest)
- Dockerfile, docker-compose
- Production deployment config, CI config
- Stripe or any payment integration
- Recommendation engine
- Email sending
- Migrations tooling (Alembic) — for this demo, `Base.metadata.create_all`
  on startup is fine
- Any external service beyond Codex itself

## Storefront rendering
After rules run and actions are dispatched:
- `ShowBanner` actions must render a visible banner on the affected 
  product's storefront page with the specified text and severity 
  (warning = red, info = blue)
- `SetVisibility` with `low_stock_badge` must show a badge on the 
  product card on the main storefront and on the product detail page
- `TagSku` tags must be stored and queryable but don't need UI 
  representation in this demo
- The storefront reads the latest dispatched action results on every 
  page load — no caching
- When a rule is deactivated or deleted, its dispatched actions are 
  cleared immediately. The storefront reflects the cleared state on 
  next page load.

## Admin routes:
- /admin - the admin dashboard landing page that the login redirects 
  to showing to buttons: Manage Inventory linking to /admin/inventory 
  and Manage Rules linking to /admin/rules
- /admin/inventory — CRUD for products (already built in Session 2)
- /admin/rules — list active rules, "Sync Now" button, sync results
- /admin/rules/generate — natural language input form, Codex output 
  diff view, Activate button
- /admin/rules — list active rules showing the original natural language 
  description (not the filename) with status badge, individual Deactivate/
  Delete button per rule, a Clear All Rules button, Sync Now button, 
  and latest sync results

## Build sessions plan

Each session is a separate Codex invocation. Commit between sessions.
Do not start a session until the previous session's acceptance criteria
are met.

### Session 1 — Scaffold and storefront
Goal: a runnable FastAPI app with a public storefront listing seeded
products.
Acceptance:
- `fastapi dev app/main.py` starts cleanly.
- Visiting `/` shows a list of at least 8 seeded clothing products with
  name, price, and stock count.
- SQLite DB created on first run, seeded automatically.
- One smoke test in `tests/test_routes_store.py` passes.

### Session 2 — Admin backend with auth
Goal: protected admin area for inventory CRUD.
Acceptance:
- `/admin/login` accepts a seeded admin user (username + password).
- `/admin/inventory` lists, creates, edits, deletes products.
- Unauthenticated access to any `/admin/*` route redirects to login.
- CSRF protection on all POST forms (hand-rolled signed token, no new
  dependencies — see Code conventions).
- Tests cover login success, login failure, and one CRUD operation.

### Session 3 — Rule engine internals (Codex NOT used at runtime here)
Goal: rule loader, executor, one hand-written example rule, and the
import validator that enforces the rule generation contract.
Acceptance:
- `rules/_base.py` defines:
  - `Rule`, `InventorySnapshot`, `Sku`
  - The closed Action union: `TagSku`, `SetVisibility`, `ShowBanner`,
    `SendNotification`
  - `validate_rule_file(path)` — a static AST check that rejects any
    rule file importing outside `rules._base` and the stdlib
- `rules/example_clearance.py` implements a working rule.
- `app/services/rule_engine.py` loads all rules (running the validator
  on each), runs them against a snapshot, dispatches actions.
- "Sync Now" button in admin runs the engine and shows results.
- `tests/rules/test_example_clearance.py` passes.
- After "Sync Now", affected products show banners or badges on the 
  public storefront reflecting the dispatched actions.

### Session 4 — Codex integration
Goal: admin types a rule in English, Codex writes the file and test
under the rule generation contract. If Codex cannot produce a passing 
rule/test after the configured retry limit, preserve the generated 
files as inactive drafts, show the pytest failure output, and do not activate the rule.
- `/admin/rules/generate` POST endpoint takes a natural-language
  description and invokes Codex via `app/services/codex_client.py`.
- Codex writes `rules/<snake_name>.py` and
  `tests/rules/test_<snake_name>.py`, runs only that test with
  `pytest tests/rules/test_<snake_name>.py -x -q`, fixes failures,
  exits clean.
- The loader's `validate_rule_file` runs on the new file before
  activation; any violation quarantines the file.
- Admin sees the generated files in a diff view with an Activate
  button. The diff view is simple `<pre>` blocks of the generated rule
  file and test file — no syntax-highlighting library, no diff library.
- Activated rules run on next "Sync Now."
- Polish: clean banner UI when a rule fires, simple "what Codex did"
  log.
- Rule listings on /admin/rules display the original natural language 
  description, not the Python filename
- Individual rules can be deactivated or deleted
- Clearing a rule immediately removes its dispatched actions from the 
  database
- A Clear All Rules button removes all rules and their dispatched actions
