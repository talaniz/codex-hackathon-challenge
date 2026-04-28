import asyncio
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from httpx import ASGITransport, AsyncClient

from app.main import create_app


def test_admin_login_success_redirects_to_inventory(tmp_path):
    async def exercise() -> None:
        async with _client(tmp_path) as client:
            csrf_token = await _csrf_token(client)
            response = await client.post(
                "/admin/login",
                data={"username": "admin", "password": "codex-demo", "csrf_token": csrf_token},
                follow_redirects=False,
            )

            assert response.status_code == 303
            assert response.headers["location"] == "/admin/inventory"

            inventory_response = await client.get("/admin/inventory")
            assert inventory_response.status_code == 200
            assert "Current Products" in inventory_response.text

    asyncio.run(exercise())


def test_admin_login_failure_shows_error(tmp_path):
    async def exercise() -> None:
        async with _client(tmp_path) as client:
            csrf_token = await _csrf_token(client)
            response = await client.post(
                "/admin/login",
                data={"username": "admin", "password": "wrong", "csrf_token": csrf_token},
            )

            assert response.status_code == 401
            assert "Invalid username or password" in response.text

    asyncio.run(exercise())


def test_admin_inventory_requires_login(tmp_path):
    async def exercise() -> None:
        async with _client(tmp_path) as client:
            response = await client.get("/admin/inventory", follow_redirects=False)

            assert response.status_code == 303
            assert response.headers["location"] == "/admin/login"

    asyncio.run(exercise())


def test_admin_inventory_crud_create_edit_delete(tmp_path):
    async def exercise() -> None:
        async with _client(tmp_path) as client:
            await _login(client)

            inventory_response = await client.get("/admin/inventory")
            csrf_token = _extract_csrf(inventory_response.text)
            create_response = await client.post(
                "/admin/inventory",
                data={
                    "csrf_token": csrf_token,
                    "slug": "test-overshirt",
                    "name": "Test Overshirt",
                    "description": "Cotton overshirt for tests.",
                    "price_cents": "5800",
                    "stock_count": "7",
                    "image_filename": "white_tshirt.jpg",
                    "category": "Tests",
                },
                follow_redirects=False,
            )
            assert create_response.status_code == 303

            inventory_response = await client.get("/admin/inventory")
            assert "Test Overshirt" in inventory_response.text
            product_id = _extract_product_id_for_slug(inventory_response.text, "test-overshirt")
            csrf_token = _extract_csrf(inventory_response.text)

            edit_response = await client.post(
                f"/admin/inventory/{product_id}/edit",
                data={
                    "csrf_token": csrf_token,
                    "slug": "test-overshirt",
                    "name": "Updated Overshirt",
                    "description": "Updated cotton overshirt.",
                    "price_cents": "6200",
                    "stock_count": "5",
                    "image_filename": "white_tshirt.jpg",
                    "category": "Tests",
                },
                follow_redirects=False,
            )
            assert edit_response.status_code == 303

            inventory_response = await client.get("/admin/inventory")
            assert "Updated Overshirt" in inventory_response.text
            csrf_token = _extract_csrf(inventory_response.text)

            delete_response = await client.post(
                f"/admin/inventory/{product_id}/delete",
                data={"csrf_token": csrf_token},
                follow_redirects=False,
            )
            assert delete_response.status_code == 303

            inventory_response = await client.get("/admin/inventory")
            assert "Updated Overshirt" not in inventory_response.text

    asyncio.run(exercise())


def test_admin_inventory_rejects_missing_csrf(tmp_path):
    async def exercise() -> None:
        async with _client(tmp_path) as client:
            await _login(client)
            response = await client.post(
                "/admin/inventory",
                data={
                    "slug": "missing-csrf",
                    "name": "Missing CSRF",
                    "description": "Rejected.",
                    "price_cents": "100",
                    "stock_count": "1",
                    "image_filename": "white_tshirt.jpg",
                    "category": "Tests",
                },
            )

            assert response.status_code == 422

    asyncio.run(exercise())


@asynccontextmanager
async def _client(tmp_path) -> AsyncIterator[AsyncClient]:
    database_url = f"sqlite:///{tmp_path / 'admin.db'}"
    app = create_app(database_url=database_url)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


async def _csrf_token(client: AsyncClient) -> str:
    response = await client.get("/admin/login")
    return _extract_csrf(response.text)


async def _login(client: AsyncClient) -> None:
    csrf_token = await _csrf_token(client)
    response = await client.post(
        "/admin/login",
        data={"username": "admin", "password": "codex-demo", "csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert response.status_code == 303


def _extract_csrf(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match is not None
    return match.group(1)


def _extract_product_id_for_slug(html: str, slug: str) -> str:
    match = re.search(rf'data-product-slug="{slug}"[\s\S]*?/admin/inventory/(\d+)/edit', html)
    assert match is not None
    return match.group(1)
