import asyncio
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from httpx import ASGITransport, AsyncClient

from app.main import create_app


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
            assert "example_clearance.py" in rules_response.text
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
