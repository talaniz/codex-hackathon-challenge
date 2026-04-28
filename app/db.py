from collections.abc import Generator

from sqlalchemy import create_engine
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


def get_session() -> Generator[Session, None, None]:
    if SessionLocal is None:
        raise RuntimeError("Database has not been configured")
    with SessionLocal() as session:
        yield session
