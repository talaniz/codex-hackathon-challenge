from app.db import Base, configure_database
from app.models import RuleFile
from app.services.inventory import seed_products
from app.services.rule_engine import (
    ACTIVE,
    build_inventory_snapshot,
    list_current_actions,
    list_rule_files,
    run_sync,
    visibility_by_sku,
)
from rules._base import RuleValidationError, validate_rule_file


def test_validate_rule_file_rejects_third_party_import(tmp_path):
    rule_path = tmp_path / "bad_rule.py"
    rule_path.write_text("import sqlalchemy\n")

    try:
        validate_rule_file(rule_path)
    except RuleValidationError as exc:
        assert "sqlalchemy" in str(exc)
    else:
        raise AssertionError("Expected third-party import to be rejected")


def test_rule_engine_sync_dispatches_low_stock_actions(tmp_path):
    session_factory = _make_session_factory(tmp_path)
    with session_factory() as session:
        seed_products(session)

        rule_files = list_rule_files(session)
        example_rule = next(rule_file for rule_file in rule_files if rule_file.filename == "example_clearance.py")
        assert example_rule.status == ACTIVE

        result = run_sync(session)
        actions = list_current_actions(session)

        assert result.loaded_count >= 1
        assert result.action_count >= 1
        assert any(action.sku == "mens-commute-hoodie" for action in actions)
        assert visibility_by_sku(session)["mens-commute-hoodie"] == "low_stock_badge"


def test_build_inventory_snapshot_returns_seeded_skus(tmp_path):
    session_factory = _make_session_factory(tmp_path)
    with session_factory() as session:
        seed_products(session)

        snapshot = build_inventory_snapshot(session)

        assert len(snapshot.skus) == 8
        assert {sku.sku for sku in snapshot.skus} >= {"mens-commute-hoodie"}


def test_inactive_draft_rule_status_is_preserved(tmp_path):
    session_factory = _make_session_factory(tmp_path)
    with session_factory() as session:
        session.add(RuleFile(filename="example_clearance.py", status="inactive_draft", status_detail="Draft"))
        session.commit()

        rule_files = list_rule_files(session)

        example_rule = next(rule_file for rule_file in rule_files if rule_file.filename == "example_clearance.py")
        assert example_rule.status == "inactive_draft"


def _make_session_factory(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'rules.db'}"
    configure_database(database_url)
    from app.db import SessionLocal

    Base.metadata.create_all(bind=SessionLocal.kw["bind"])
    return SessionLocal
