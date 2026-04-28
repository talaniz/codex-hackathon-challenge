from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///./codex_store.db"
    secret_key: str = "dev-secret-change-me"
    admin_username: str = "admin"
    admin_password: str = "codex-demo"


def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./codex_store.db"),
        secret_key=os.getenv("SECRET_KEY", "dev-secret-change-me"),
        admin_username=os.getenv("ADMIN_USERNAME", "admin"),
        admin_password=os.getenv("ADMIN_PASSWORD", "codex-demo"),
    )
