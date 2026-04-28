from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import DispatchedRuleAction, Product, RuleFile, RuleSyncRun
from rules._base import (
    Action,
    InventorySnapshot,
    Rule,
    RuleValidationError,
    SendNotification,
    SetVisibility,
    ShowBanner,
    Sku,
    TagSku,
    validate_rule_file,
)


RULES_DIR = Path("rules")
ACTIVE = "active"
QUARANTINED = "quarantined"
INACTIVE_DRAFT = "inactive_draft"


@dataclass(frozen=True)
class LoadedRule:
    filename: str
    rule: Rule


@dataclass(frozen=True)
class SyncResult:
    sync_run_id: int
    loaded_count: int
    action_count: int
    quarantined_count: int
    summary: str


def list_rule_files(session: Session) -> list[RuleFile]:
    for path in _iter_rule_paths():
        record = _get_or_create_rule_file(session, path.name)
        try:
            validate_rule_file(path)
            _load_rule(path)
        except RuleValidationError as exc:
            record.status = QUARANTINED
            record.status_detail = str(exc)
        except Exception as exc:
            record.status = QUARANTINED
            record.status_detail = f"{path.name} is not loadable: {exc}"
        else:
            if record.status != INACTIVE_DRAFT:
                record.status = ACTIVE
                record.status_detail = ""
    session.commit()
    return list(session.scalars(select(RuleFile).order_by(RuleFile.filename)).all())


def load_active_rules(session: Session) -> list[LoadedRule]:
    files = list_rule_files(session)
    loaded_rules: list[LoadedRule] = []
    for record in files:
        if record.status != ACTIVE:
            continue
        path = RULES_DIR / record.filename
        try:
            loaded_rules.append(LoadedRule(record.filename, _load_rule(path)))
        except Exception as exc:
            record.status = QUARANTINED
            record.status_detail = str(exc)
    session.commit()
    return loaded_rules


def run_sync(session: Session) -> SyncResult:
    rules = load_active_rules(session)
    snapshot = build_inventory_snapshot(session)
    actions_by_rule: list[tuple[str, Action]] = []
    quarantined_count = _count_quarantined(session)

    for loaded_rule in rules:
        try:
            actions = loaded_rule.rule.evaluate(snapshot)
            for action in actions:
                _validate_action(action)
        except Exception as exc:
            _quarantine_rule(session, loaded_rule.filename, f"Rule execution failed: {exc}")
            quarantined_count += 1
            continue
        for action in actions:
            actions_by_rule.append((loaded_rule.filename, action))

    session.execute(delete(DispatchedRuleAction))
    sync_run = RuleSyncRun(
        summary=(
            f"Loaded {len(rules)} active rule file(s), dispatched "
            f"{len(actions_by_rule)} action(s), quarantined {quarantined_count} file(s)."
        )
    )
    session.add(sync_run)
    session.flush()
    for filename, action in actions_by_rule:
        session.add(_action_record(sync_run.id, filename, action))
    session.commit()
    return SyncResult(
        sync_run_id=sync_run.id,
        loaded_count=len(rules),
        action_count=len(actions_by_rule),
        quarantined_count=quarantined_count,
        summary=sync_run.summary,
    )


def build_inventory_snapshot(session: Session) -> InventorySnapshot:
    products = session.scalars(select(Product).order_by(Product.slug)).all()
    return InventorySnapshot(
        skus=tuple(
            Sku(
                sku=product.slug,
                name=product.name,
                category=product.category,
                price_cents=product.price_cents,
                stock_count=product.stock_count,
            )
            for product in products
        )
    )


def latest_sync_run(session: Session) -> RuleSyncRun | None:
    return session.scalar(select(RuleSyncRun).order_by(RuleSyncRun.id.desc()).limit(1))


def list_current_actions(session: Session) -> list[DispatchedRuleAction]:
    return list(
        session.scalars(select(DispatchedRuleAction).order_by(DispatchedRuleAction.rule_filename, DispatchedRuleAction.id)).all()
    )


def visibility_by_sku(session: Session) -> dict[str, str]:
    actions = session.scalars(
        select(DispatchedRuleAction).where(DispatchedRuleAction.action_type == "set_visibility")
    )
    return {
        action.sku: action.visibility_state
        for action in actions
        if action.sku is not None and action.visibility_state is not None
    }


def banners_for_sku(session: Session, sku: str) -> list[DispatchedRuleAction]:
    return list(
        session.scalars(
            select(DispatchedRuleAction)
            .where(
                DispatchedRuleAction.action_type == "show_banner",
                (DispatchedRuleAction.sku == sku) | (DispatchedRuleAction.sku.is_(None)),
            )
            .order_by(DispatchedRuleAction.id)
        ).all()
    )


def _iter_rule_paths() -> list[Path]:
    if not RULES_DIR.exists():
        return []
    return sorted(path for path in RULES_DIR.glob("*.py") if not path.name.startswith("_") and path.name != "__init__.py")


def _get_or_create_rule_file(session: Session, filename: str) -> RuleFile:
    record = session.scalar(select(RuleFile).where(RuleFile.filename == filename))
    if record is None:
        record = RuleFile(filename=filename, status=ACTIVE, status_detail="")
        session.add(record)
        session.flush()
    return record


def _load_rule(path: Path) -> Rule:
    validate_rule_file(path)
    module_name = f"rules.dynamic_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rule = getattr(module, "RULE")
    if not isinstance(rule, Rule):
        raise TypeError(f"{path.name} must expose RULE as rules._base.Rule")
    return rule


def _validate_action(action: Action) -> None:
    if not isinstance(action, TagSku | SetVisibility | ShowBanner | SendNotification):
        raise TypeError(f"Unsupported rule action: {action!r}")


def _action_record(sync_run_id: int, filename: str, action: Action) -> DispatchedRuleAction:
    if isinstance(action, TagSku):
        return DispatchedRuleAction(
            sync_run_id=sync_run_id,
            rule_filename=filename,
            action_type="tag_sku",
            sku=action.sku,
            tag=action.tag,
        )
    if isinstance(action, SetVisibility):
        return DispatchedRuleAction(
            sync_run_id=sync_run_id,
            rule_filename=filename,
            action_type="set_visibility",
            sku=action.sku,
            visibility_state=action.state,
        )
    if isinstance(action, ShowBanner):
        return DispatchedRuleAction(
            sync_run_id=sync_run_id,
            rule_filename=filename,
            action_type="show_banner",
            banner_text=action.text,
            banner_severity=action.severity,
        )
    return DispatchedRuleAction(
        sync_run_id=sync_run_id,
        rule_filename=filename,
        action_type="send_notification",
        notification_channel=action.channel,
        notification_text=action.text,
    )


def _quarantine_rule(session: Session, filename: str, detail: str) -> None:
    record = _get_or_create_rule_file(session, filename)
    record.status = QUARANTINED
    record.status_detail = detail


def _count_quarantined(session: Session) -> int:
    return len(session.scalars(select(RuleFile).where(RuleFile.status == QUARANTINED)).all())
