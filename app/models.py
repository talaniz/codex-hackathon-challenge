from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(600))
    price_cents: Mapped[int] = mapped_column(Integer)
    stock_count: Mapped[int] = mapped_column(Integer)
    image_filename: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(80))


class RuleFile(Base):
    __tablename__ = "rule_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    status_detail: Mapped[str] = mapped_column(Text, default="")


class RuleSyncRun(Base):
    __tablename__ = "rule_sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    summary: Mapped[str] = mapped_column(Text, default="")


class DispatchedRuleAction(Base):
    __tablename__ = "dispatched_rule_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    sync_run_id: Mapped[int] = mapped_column(ForeignKey("rule_sync_runs.id"), index=True)
    rule_filename: Mapped[str] = mapped_column(String(160), index=True)
    action_type: Mapped[str] = mapped_column(String(40), index=True)
    sku: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    tag: Mapped[str | None] = mapped_column(String(80), nullable=True)
    visibility_state: Mapped[str | None] = mapped_column(String(40), nullable=True)
    banner_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    banner_severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notification_channel: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notification_text: Mapped[str | None] = mapped_column(Text, nullable=True)
