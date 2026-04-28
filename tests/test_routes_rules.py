import asyncio
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.models import RuleFile
from app.services.codex_client import RuleGenerationResult


def test_admin_rules_requires_login(tmp_path):
    async def exercise() -> None:
        async with _client(tmp_path) as client:
            response = await client.get("/admin/rules", follow_redirects=False)

            assert response.status_code == 303
            assert response.headers["location"] == "/admin/login"

    asyncio.run(exercise())


def test_admin_rules_sync_updates_storefront_badges(tmp_path):
    async def exercise() -> None:
        async with _client(tmp_path) as client:
            await _login(client)

            rules_response = await client.get("/admin/rules")
            assert rules_response.status_code == 200
            assert "Marks products at or below the low-stock threshold" in rules_response.text
            csrf_token = _extract_csrf(rules_response.text)

            sync_response = await client.post(
                "/admin/rules/sync",
                data={"csrf_token": csrf_token},
                follow_redirects=False,
            )
            assert sync_response.status_code == 303
            assert sync_response.headers["location"] == "/admin/rules"

            rules_response = await client.get("/admin/rules")
            assert "Dispatched Actions" in rules_response.text
            assert "mens-commute-hoodie" in rules_response.text

            storefront_response = await client.get("/")
            assert "Low stock" in storefront_response.text

            detail_response = await client.get("/products/mens-commute-hoodie")
            assert "Low stock" in detail_response.text

    asyncio.run(exercise())


def test_admin_rules_generate_shows_inactive_draft(monkeypatch, tmp_path):
    rule_path = Path("rules/session4_generated_route.py")
    test_path = Path("tests/rules/test_session4_generated_route.py")

    def fake_generate_rule_draft(session, description):
        rule_source = (
            "from rules._base import InventorySnapshot, Rule\n\n"
            "def evaluate(snapshot: InventorySnapshot):\n"
            "    return []\n\n"
            "RULE = Rule(name='Route test', description='Route generated rule', evaluate=evaluate)\n"
        )
        test_source = "def test_route_generated_rule():\n    assert True\n"
        rule_path.write_text(rule_source)
        test_path.write_text(test_source)
        record = RuleFile(
            filename=rule_path.name,
            test_filename=str(test_path),
            description=description,
            status="inactive_draft",
            status_detail="Ready to activate.",
            generation_log="1 passed",
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return RuleGenerationResult(record, rule_source, test_source, "1 passed", True)

    monkeypatch.setattr("app.routes.rules.generate_rule_draft", fake_generate_rule_draft)

    async def exercise() -> None:
        try:
            async with _client(tmp_path) as client:
                await _login(client)
                rules_response = await client.get("/admin/rules")
                csrf_token = _extract_csrf(rules_response.text)

                response = await client.post(
                    "/admin/rules/generate",
                    data={
                        "csrf_token": csrf_token,
                        "description": "Show a route test banner",
                    },
                )

                assert response.status_code == 200
                assert "Codex Output" in response.text
                assert "Show a route test banner" in response.text
                assert "inactive draft" in response.text
                assert "Activate" in response.text
        finally:
            rule_path.unlink(missing_ok=True)
            test_path.unlink(missing_ok=True)

    asyncio.run(exercise())


def test_admin_rules_activate_syncs_banner_rule(tmp_path):
    rule_path = Path("rules/session4_activation_banner_route.py")
    test_path = Path("tests/rules/test_session4_activation_banner_route.py")
    rule_source = (
        "from rules._base import InventorySnapshot, Rule, ShowBanner\n\n"
        "def evaluate(snapshot: InventorySnapshot):\n"
        "    for sku in snapshot.skus:\n"
        "        if 'hoodie' in sku.name.lower() and sku.stock_count < 10:\n"
        "            return [ShowBanner(text='Hoodies are running low.', severity='warning')]\n"
        "    return []\n\n"
        "RULE = Rule(name='Activation banner route', description='Banner on activation.', evaluate=evaluate)\n"
    )

    async def exercise() -> None:
        try:
            rule_path.write_text(rule_source)
            test_path.write_text("def test_placeholder():\n    assert True\n")
            async with _client(tmp_path) as client:
                from app.db import SessionLocal

                with SessionLocal() as session:
                    record = RuleFile(
                        filename=rule_path.name,
                        test_filename=str(test_path),
                        description="Banner on activation.",
                        status="inactive_draft",
                        status_detail="Ready to activate.",
                        generation_log="1 passed",
                    )
                    session.add(record)
                    session.commit()
                    rule_id = record.id

                await _login(client)
                rules_response = await client.get("/admin/rules")
                csrf_token = _extract_csrf(rules_response.text)

                response = await client.post(
                    f"/admin/rules/{rule_id}/activate",
                    data={"csrf_token": csrf_token},
                    follow_redirects=False,
                )

                assert response.status_code == 303
                detail_response = await client.get("/products/mens-commute-hoodie")
                assert "Hoodies are running low." in detail_response.text
                assert "banner-warning" in detail_response.text
        finally:
            rule_path.unlink(missing_ok=True)
            test_path.unlink(missing_ok=True)

    asyncio.run(exercise())


@asynccontextmanager
async def _client(tmp_path) -> AsyncIterator[AsyncClient]:
    database_url = f"sqlite:///{tmp_path / 'routes-rules.db'}"
    app = create_app(database_url=database_url)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


async def _login(client: AsyncClient) -> None:
    response = await client.get("/admin/login")
    csrf_token = _extract_csrf(response.text)
    login_response = await client.post(
        "/admin/login",
        data={"username": "admin", "password": "codex-demo", "csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert login_response.status_code == 303


def _extract_csrf(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match is not None
    return match.group(1)
