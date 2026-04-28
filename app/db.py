from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


_engine = None
SessionLocal: sessionmaker[Session] | None = None


def configure_database(database_url: str) -> None:
    global _engine, SessionLocal
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    _engine = create_engine(database_url, connect_args=connect_args)
    SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)


def create_db() -> None:
    if _engine is None:
        raise RuntimeError("Database has not been configured")
    Base.metadata.create_all(bind=_engine)
    upgrade_db_schema()


def upgrade_db_schema() -> None:
    if _engine is None:
        raise RuntimeError("Database has not been configured")
    inspector = inspect(_engine)
    if "rule_files" not in inspector.get_table_names():
        return
    existing_columns = {column["name"] for column in inspector.get_columns("rule_files")}
    columns = {
        "test_filename": "VARCHAR(180) NOT NULL DEFAULT ''",
        "description": "TEXT NOT NULL DEFAULT ''",
        "generation_log": "TEXT NOT NULL DEFAULT ''",
    }
    with _engine.begin() as connection:
        for name, definition in columns.items():
            if name not in existing_columns:
                connection.execute(text(f"ALTER TABLE rule_files ADD COLUMN {name} {definition}"))


def get_session() -> Generator[Session, None, None]:
    if SessionLocal is None:
        raise RuntimeError("Database has not been configured")
    with SessionLocal() as session:
        yield session
