import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import create_app


def test_storefront_lists_seeded_products(tmp_path):
    async def exercise() -> None:
        database_url = f"sqlite:///{tmp_path / 'store.db'}"
        app = create_app(database_url=database_url)
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/")

        assert response.status_code == 200
        assert "Men&#39;s Everyday Hoodie" in response.text
        assert "Classic White T-Shirt" in response.text
        assert "$68.00" in response.text
        assert "24 in stock" in response.text
        assert response.text.count("product-card") >= 8
        assert "/static/main_page.jpg" in response.text
        assert "/products/mens-everyday-hoodie" in response.text

    asyncio.run(exercise())
