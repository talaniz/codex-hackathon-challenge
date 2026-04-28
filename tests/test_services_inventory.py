from app.db import Base, configure_database
from app.models import Product
from app.services.inventory import (
    create_product,
    delete_product,
    get_product,
    get_product_by_slug,
    get_product_by_slug_excluding_id,
    list_products,
    seed_products,
    update_product,
)


def test_seed_and_list_products(tmp_path):
    session_factory = _make_session_factory(tmp_path)
    with session_factory() as session:
        seed_products(session)
        products = list_products(session)

    assert len(products) == 8
    assert products[0].name


def test_get_product_by_slug_returns_none_for_missing_slug(tmp_path):
    session_factory = _make_session_factory(tmp_path)
    with session_factory() as session:
        seed_products(session)
        product = get_product_by_slug(session, "missing-product")

    assert product is None


def test_inventory_crud_services(tmp_path):
    session_factory = _make_session_factory(tmp_path)
    with session_factory() as session:
        product = create_product(
            session,
            slug="service-shirt",
            name="Service Shirt",
            description="Created by service tests.",
            price_cents=3100,
            stock_count=4,
            image_filename="white_tshirt.jpg",
            category="Tests",
        )

        assert get_product(session, product.id).name == "Service Shirt"
        assert get_product(session, 999999) is None
        assert get_product_by_slug_excluding_id(session, "service-shirt", product.id) is None
        assert get_product_by_slug_excluding_id(session, "service-shirt", 999999).id == product.id

        updated = update_product(
            session,
            product,
            slug="service-shirt",
            name="Updated Service Shirt",
            description="Updated by service tests.",
            price_cents=3500,
            stock_count=2,
            image_filename="white_tshirt.jpg",
            category="Tests",
        )
        assert updated.name == "Updated Service Shirt"

        delete_product(session, updated)
        assert get_product(session, product.id) is None


def _make_session_factory(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'inventory.db'}"
    configure_database(database_url)
    from app.db import SessionLocal

    Base.metadata.create_all(bind=SessionLocal.kw["bind"])
    return SessionLocal
