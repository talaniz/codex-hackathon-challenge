from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///./codex_store.db"


def get_settings() -> Settings:
    return Settings(database_url=os.getenv("DATABASE_URL", "sqlite:///./codex_store.db"))
