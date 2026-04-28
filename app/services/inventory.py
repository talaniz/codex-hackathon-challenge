from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Product


SEED_PRODUCTS = [
    {
        "slug": "mens-everyday-hoodie",
        "name": "Men's Everyday Hoodie",
        "description": "A midweight fleece hoodie with a clean fit for daily wear.",
        "price_cents": 6800,
        "stock_count": 24,
        "image_filename": "mens_hoodie.jpg",
        "category": "Men",
    },
    {
        "slug": "classic-white-tshirt",
        "name": "Classic White T-Shirt",
        "description": "Soft cotton jersey tee with a straight silhouette.",
        "price_cents": 2400,
        "stock_count": 41,
        "image_filename": "white_tshirt.jpg",
        "category": "Basics",
    },
    {
        "slug": "straight-leg-denim",
        "name": "Straight Leg Denim",
        "description": "Durable denim jeans with a versatile medium wash.",
        "price_cents": 7900,
        "stock_count": 18,
        "image_filename": "jeans.jpg",
        "category": "Denim",
    },
    {
        "slug": "mens-textured-sweater",
        "name": "Men's Textured Sweater",
        "description": "Warm knit sweater with ribbed cuffs and an easy layered shape.",
        "price_cents": 7200,
        "stock_count": 13,
        "image_filename": "sweater_mens.jpg",
        "category": "Men",
    },
    {
        "slug": "womens-cropped-hoodie",
        "name": "Women's Cropped Hoodie",
        "description": "A soft cropped hoodie designed for relaxed weekend styling.",
        "price_cents": 6400,
        "stock_count": 29,
        "image_filename": "womens_hoodie.jpg",
        "category": "Women",
    },
    {
        "slug": "womens-ribbed-sweater",
        "name": "Women's Ribbed Sweater",
        "description": "Fine rib knit sweater with a polished neckline and soft handfeel.",
        "price_cents": 7400,
        "stock_count": 16,
        "image_filename": "sweater_womens.jpg",
        "category": "Women",
    },
    {
        "slug": "mens-commute-hoodie",
        "name": "Men's Commute Hoodie",
        "description": "A darker hoodie option with enough structure for layered outfits.",
        "price_cents": 7000,
        "stock_count": 9,
        "image_filename": "mens_hoodie.jpg",
        "category": "Men",
    },
    {
        "slug": "weekend-white-tee",
        "name": "Weekend White Tee",
        "description": "A lightweight white tee for warm days and year-round layering.",
        "price_cents": 2200,
        "stock_count": 35,
        "image_filename": "white_tshirt.jpg",
        "category": "Basics",
    },
]


def seed_products(session: Session) -> None:
    existing = session.scalar(select(Product.id).limit(1))
    if existing is not None:
        return
    session.add_all(Product(**product) for product in SEED_PRODUCTS)
    session.commit()


def list_products(session: Session) -> list[Product]:
    return list(session.scalars(select(Product).order_by(Product.name)).all())


def get_product_by_slug(session: Session, slug: str) -> Product | None:
    return session.scalar(select(Product).where(Product.slug == slug))
