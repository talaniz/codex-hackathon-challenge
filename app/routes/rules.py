from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import ensure_csrf_token, require_admin, validate_csrf, write_session
from app.db import get_session
from app.models import AdminUser
from app.services.rule_engine import latest_sync_run, list_current_actions, list_rule_files, run_sync


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


def _rules_response(request: Request, session: Session):
    csrf_token, session_data = ensure_csrf_token(request)
    response = templates.TemplateResponse(
        request,
        "pages/admin_rules.html",
        {
            "csrf_token": csrf_token,
            "rule_files": list_rule_files(session),
            "latest_sync": latest_sync_run(session),
            "actions": list_current_actions(session),
        },
    )
    write_session(response, session_data)
    return response
