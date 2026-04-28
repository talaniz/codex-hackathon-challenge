from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import ensure_csrf_token, require_admin, validate_csrf, write_session
from app.db import get_session
from app.models import AdminUser
from app.services.codex_client import generate_rule_draft
from app.services.rule_engine import (
    ACTIVE,
    activate_rule,
    clear_active_rules,
    deactivate_rule,
    delete_rule,
    latest_sync_run,
    list_current_actions,
    list_rule_files,
    run_sync,
)


router = APIRouter(prefix="/admin/rules")
templates = Jinja2Templates(directory="app/templates")

SessionDep = Annotated[Session, Depends(get_session)]
AdminDep = Annotated[AdminUser, Depends(require_admin)]
CsrfDep = Annotated[None, Depends(validate_csrf)]


@router.get("")
def rules_index(request: Request, session: SessionDep, _: AdminDep):
    return _rules_response(request, session)


@router.post("/sync")
def rules_sync(request: Request, session: SessionDep, _: AdminDep, __: CsrfDep):
    run_sync(session)
    response = RedirectResponse("/admin/rules", status_code=303)
    _, session_data = ensure_csrf_token(request)
    write_session(response, session_data)
    return response


@router.get("/generate")
def rules_generate_form(request: Request, session: SessionDep, _: AdminDep):
    return _rules_response(request, session)


@router.post("/generate")
def rules_generate(
    request: Request,
    session: SessionDep,
    _: AdminDep,
    __: CsrfDep,
    description: Annotated[str, Form()],
):
    try:
        generated = generate_rule_draft(session, description)
    except ValueError as exc:
        return _rules_response(request, session, error=str(exc), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:
        return _rules_response(
            request,
            session,
            error=f"Codex could not generate the rule: {exc}",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
    return _rules_response(request, session, generated=generated)


@router.post("/{rule_file_id}/activate")
def rules_activate(rule_file_id: int, session: SessionDep, _: AdminDep, __: CsrfDep):
    rule_file = activate_rule(session, rule_file_id)
    if rule_file is None:
        raise HTTPException(status_code=404)
    if rule_file.status == ACTIVE:
        run_sync(session)
    return RedirectResponse("/admin/rules", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{rule_file_id}/deactivate")
def rules_deactivate(rule_file_id: int, session: SessionDep, _: AdminDep, __: CsrfDep):
    if deactivate_rule(session, rule_file_id) is None:
        raise HTTPException(status_code=404)
    return RedirectResponse("/admin/rules", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{rule_file_id}/delete")
def rules_delete(rule_file_id: int, session: SessionDep, _: AdminDep, __: CsrfDep):
    if not delete_rule(session, rule_file_id):
        raise HTTPException(status_code=404)
    return RedirectResponse("/admin/rules", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/clear-active")
def rules_clear_active(session: SessionDep, _: AdminDep, __: CsrfDep):
    clear_active_rules(session)
    return RedirectResponse("/admin/rules", status_code=status.HTTP_303_SEE_OTHER)


def _rules_response(request: Request, session: Session, error: str | None = None, generated=None, status_code: int = 200):
    csrf_token, session_data = ensure_csrf_token(request)
    response = templates.TemplateResponse(
        request,
        "pages/admin_rules.html",
        {
            "csrf_token": csrf_token,
            "rule_files": list_rule_files(session),
            "latest_sync": latest_sync_run(session),
            "actions": list_current_actions(session),
            "error": error,
            "generated": generated,
        },
        status_code=status_code,
    )
    write_session(response, session_data)
    return response
