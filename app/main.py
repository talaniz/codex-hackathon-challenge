from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db import configure_database, create_db
from app.routes import admin, rules, store
from app.auth import seed_admin_user
from app.services.inventory import seed_products


def create_app(database_url: str | None = None) -> FastAPI:
    settings = get_settings()
    configure_database(database_url or settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        create_db()
        from app.db import SessionLocal

        if SessionLocal is None:
            raise RuntimeError("Database has not been configured")
        with SessionLocal() as session:
            seed_products(session)
            seed_admin_user(session)
        yield

    app = FastAPI(title="Codex Clothiers", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.include_router(store.router)
    app.include_router(admin.router)
    app.include_router(rules.router)
    return app


app = create_app()
