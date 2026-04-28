from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import (
    authenticate_admin,
    clear_session,
    ensure_csrf_token,
    require_admin,
    validate_csrf,
    write_session,
)
from app.db import get_session
from app.models import AdminUser
from app.services.inventory import (
    create_product,
    delete_product,
    get_product,
    get_product_by_slug,
    get_product_by_slug_excluding_id,
    list_products,
    update_product,
)


router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")

SessionDep = Annotated[Session, Depends(get_session)]
AdminDep = Annotated[AdminUser, Depends(require_admin)]
CsrfDep = Annotated[None, Depends(validate_csrf)]


@router.get("/login")
def login_form(request: Request):
    csrf_token, session_data = ensure_csrf_token(request)
    response = templates.TemplateResponse(
        request,
        "pages/admin_login.html",
        {"csrf_token": csrf_token, "error": None},
    )
    write_session(response, session_data)
    return response


@router.post("/login")
def login(
    request: Request,
    session: SessionDep,
    _: CsrfDep,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    admin = authenticate_admin(session, username, password)
    if admin is None:
        csrf_token, session_data = ensure_csrf_token(request)
        response = templates.TemplateResponse(
            request,
            "pages/admin_login.html",
            {"csrf_token": csrf_token, "error": "Invalid username or password"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
        write_session(response, session_data)
        return response

    session_data = {"admin_id": admin.id}
    response = RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)
    write_session(response, session_data)
    return response


@router.post("/logout")
def logout(_: AdminDep, __: CsrfDep):
    response = RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    clear_session(response)
    return response


@router.get("")
def admin_dashboard(request: Request, _: AdminDep):
    csrf_token, session_data = ensure_csrf_token(request)
    response = templates.TemplateResponse(
        request,
        "pages/admin_dashboard.html",
        {"csrf_token": csrf_token},
    )
    write_session(response, session_data)
    return response


@router.get("/inventory")
def inventory_index(request: Request, session: SessionDep, _: AdminDep):
    csrf_token, session_data = ensure_csrf_token(request)
    products = list_products(session)
    response = templates.TemplateResponse(
        request,
        "pages/admin_inventory.html",
        {"products": products, "csrf_token": csrf_token, "error": None},
    )
    write_session(response, session_data)
    return response


@router.post("/inventory")
def inventory_create(
    request: Request,
    session: SessionDep,
    _: AdminDep,
    __: CsrfDep,
    slug: Annotated[str, Form()],
    name: Annotated[str, Form()],
    description: Annotated[str, Form()],
    price_cents: Annotated[int, Form()],
    stock_count: Annotated[int, Form()],
    image_filename: Annotated[str, Form()],
    category: Annotated[str, Form()],
):
    error = _validate_product_form(session, slug=slug, price_cents=price_cents, stock_count=stock_count)
    if error is not None:
        return _inventory_response(request, session, error, status.HTTP_400_BAD_REQUEST)

    create_product(
        session,
        slug=slug,
        name=name,
        description=description,
        price_cents=price_cents,
        stock_count=stock_count,
        image_filename=image_filename,
        category=category,
    )
    return RedirectResponse("/admin/inventory", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/inventory/{product_id}/edit")
def inventory_edit(
    request: Request,
    product_id: int,
    session: SessionDep,
    _: AdminDep,
    __: CsrfDep,
    slug: Annotated[str, Form()],
    name: Annotated[str, Form()],
    description: Annotated[str, Form()],
    price_cents: Annotated[int, Form()],
    stock_count: Annotated[int, Form()],
    image_filename: Annotated[str, Form()],
    category: Annotated[str, Form()],
):
    product = get_product(session, product_id)
    if product is None:
        raise HTTPException(status_code=404)
    error = _validate_product_form(
        session,
        slug=slug,
        price_cents=price_cents,
        stock_count=stock_count,
        product_id=product_id,
    )
    if error is not None:
        return _inventory_response(request, session, error, status.HTTP_400_BAD_REQUEST)

    update_product(
        session,
        product,
        slug=slug,
        name=name,
        description=description,
        price_cents=price_cents,
        stock_count=stock_count,
        image_filename=image_filename,
        category=category,
    )
    return RedirectResponse("/admin/inventory", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/inventory/{product_id}/delete")
def inventory_delete(product_id: int, session: SessionDep, _: AdminDep, __: CsrfDep):
    product = get_product(session, product_id)
    if product is None:
        raise HTTPException(status_code=404)
    delete_product(session, product)
    return RedirectResponse("/admin/inventory", status_code=status.HTTP_303_SEE_OTHER)


def _inventory_response(request: Request, session: Session, error: str, status_code: int):
    csrf_token, session_data = ensure_csrf_token(request)
    response = templates.TemplateResponse(
        request,
        "pages/admin_inventory.html",
        {"products": list_products(session), "csrf_token": csrf_token, "error": error},
        status_code=status_code,
    )
    write_session(response, session_data)
    return response


def _validate_product_form(
    session: Session,
    *,
    slug: str,
    price_cents: int,
    stock_count: int,
    product_id: int | None = None,
) -> str | None:
    if price_cents < 0:
        return "Price must be zero or greater."
    if stock_count < 0:
        return "Stock must be zero or greater."
    existing = (
        get_product_by_slug_excluding_id(session, slug, product_id)
        if product_id is not None
        else get_product_by_slug(session, slug)
    )
    if existing is not None:
        return "Slug is already in use."
    return None
