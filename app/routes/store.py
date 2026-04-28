from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db import get_session
from app.services.inventory import get_product_by_slug, list_products
from app.services.rule_engine import banners_for_sku, visibility_by_sku


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/")
def storefront(request: Request, session: SessionDep):
    products = list_products(session)
    visibility = visibility_by_sku(session)
    return templates.TemplateResponse(
        request,
        "pages/storefront.html",
        {"products": products, "visibility": visibility},
    )


@router.get("/products/{slug}")
def product_detail(request: Request, slug: str, session: SessionDep):
    product = get_product_by_slug(session, slug)
    if product is None:
        raise HTTPException(status_code=404)
    visibility = visibility_by_sku(session)
    return templates.TemplateResponse(
        request,
        "pages/product_detail.html",
        {
            "product": product,
            "visibility_state": visibility.get(product.slug),
            "banners": banners_for_sku(session, product.slug),
        },
    )
