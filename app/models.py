from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(600))
    price_cents: Mapped[int] = mapped_column(Integer)
    stock_count: Mapped[int] = mapped_column(Integer)
    image_filename: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(80))
