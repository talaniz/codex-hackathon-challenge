from pathlib import Path

from app.db import Base, configure_database
from app.models import RuleFile
from app.services.inventory import seed_products
from app.services.rule_engine import (
    ACTIVE,
    INACTIVE,
    activate_rule,
    build_inventory_snapshot,
    clear_active_rules,
    deactivate_rule,
    delete_rule,
    discount_percent_by_sku,
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


def test_deactivate_rule_cleans_dispatched_actions(tmp_path):
    session_factory = _make_session_factory(tmp_path)
    with session_factory() as session:
        seed_products(session)
        rule_file = next(rule_file for rule_file in list_rule_files(session) if rule_file.filename == "example_clearance.py")
        run_sync(session)
        assert any(action.rule_filename == "example_clearance.py" for action in list_current_actions(session))

        updated = deactivate_rule(session, rule_file.id)

        assert updated is not None
        assert updated.status == INACTIVE
        assert not any(action.rule_filename == "example_clearance.py" for action in list_current_actions(session))


def test_discount_percent_by_sku_reads_discount_tags(tmp_path):
    rule_path, test_path = _write_discount_rule("session4_discount_rule")
    session_factory = _make_session_factory(tmp_path)
    try:
        with session_factory() as session:
            seed_products(session)
            list_rule_files(session)

            run_sync(session)

            assert discount_percent_by_sku(session)["mens-commute-hoodie"] == 15
    finally:
        rule_path.unlink(missing_ok=True)
        test_path.unlink(missing_ok=True)


def test_delete_rule_removes_files_and_actions(tmp_path):
    rule_path, test_path = _write_generated_rule("session4_delete_rule")
    session_factory = _make_session_factory(tmp_path)
    try:
        with session_factory() as session:
            seed_products(session)
            rule_file = next(rule_file for rule_file in list_rule_files(session) if rule_file.filename == rule_path.name)
            run_sync(session)
            assert any(action.rule_filename == rule_path.name for action in list_current_actions(session))

            assert delete_rule(session, rule_file.id)

            assert not rule_path.exists()
            assert not test_path.exists()
            assert not any(action.rule_filename == rule_path.name for action in list_current_actions(session))
    finally:
        rule_path.unlink(missing_ok=True)
        test_path.unlink(missing_ok=True)


def test_clear_active_rules_only_removes_active_records(tmp_path):
    rule_path, test_path = _write_generated_rule("session4_clear_rule")
    session_factory = _make_session_factory(tmp_path)
    try:
        with session_factory() as session:
            seed_products(session)
            clear_rule = next(rule_file for rule_file in list_rule_files(session) if rule_file.filename == rule_path.name)
            example_rule = next(rule_file for rule_file in list_rule_files(session) if rule_file.filename == "example_clearance.py")
            deactivate_rule(session, example_rule.id)
            run_sync(session)
            assert any(action.rule_filename == rule_path.name for action in list_current_actions(session))

            removed_count = clear_active_rules(session)

            assert removed_count >= 1
            assert not rule_path.exists()
            assert session.get(type(clear_rule), clear_rule.id) is None
            assert session.get(type(example_rule), example_rule.id).status == INACTIVE
            assert not any(action.rule_filename == rule_path.name for action in list_current_actions(session))
    finally:
        rule_path.unlink(missing_ok=True)
        test_path.unlink(missing_ok=True)


def test_activate_quarantines_invalid_rule(tmp_path):
    rule_path = _write_invalid_rule("session4_invalid_rule")
    session_factory = _make_session_factory(tmp_path)
    try:
        with session_factory() as session:
            seed_products(session)
            rule_file = next(rule_file for rule_file in list_rule_files(session) if rule_file.filename == rule_path.name)

            activated = activate_rule(session, rule_file.id)

            assert activated is not None
            assert activated.status == "quarantined"
            assert "disallowed module" in activated.status_detail
    finally:
        rule_path.unlink(missing_ok=True)


def _make_session_factory(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'rules.db'}"
    configure_database(database_url)
    from app.db import SessionLocal

    Base.metadata.create_all(bind=SessionLocal.kw["bind"])
    return SessionLocal


def _write_generated_rule(name: str):
    rule_path = Path("rules") / f"{name}.py"
    test_path = Path("tests/rules") / f"test_{name}.py"
    rule_path.write_text(
        "from rules._base import InventorySnapshot, Rule, SetVisibility\n\n"
        "def evaluate(snapshot: InventorySnapshot):\n"
        "    return [\n"
        "        SetVisibility(sku=sku.sku, state='low_stock_badge')\n"
        "        for sku in snapshot.skus\n"
        "        if sku.sku == 'mens-commute-hoodie'\n"
        "    ]\n\n"
        f"RULE = Rule(name='{name}', description='Generated cleanup test rule.', evaluate=evaluate)\n"
    )
    test_path.write_text("def test_placeholder():\n    assert True\n")
    return rule_path, test_path


def _write_discount_rule(name: str):
    rule_path = Path("rules") / f"{name}.py"
    test_path = Path("tests/rules") / f"test_{name}.py"
    rule_path.write_text(
        "from rules._base import InventorySnapshot, Rule, TagSku\n\n"
        "def evaluate(snapshot: InventorySnapshot):\n"
        "    return [TagSku(sku=sku.sku, tag='spring-wide-15-discount') for sku in snapshot.skus]\n\n"
        f"RULE = Rule(name='{name}', description='Generated discount tag test rule.', evaluate=evaluate)\n"
    )
    test_path.write_text("def test_placeholder():\n    assert True\n")
    return rule_path, test_path


def _write_invalid_rule(name: str):
    rule_path = Path("rules") / f"{name}.py"
    rule_path.write_text("import sqlalchemy\n")
    return rule_path
