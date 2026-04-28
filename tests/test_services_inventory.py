from app.db import Base, configure_database
from app.models import Product
from app.services.inventory import get_product_by_slug, list_products, seed_products


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


def _make_session_factory(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'inventory.db'}"
    configure_database(database_url)
    from app.db import SessionLocal

    Base.metadata.create_all(bind=SessionLocal.kw["bind"])
    return SessionLocal
