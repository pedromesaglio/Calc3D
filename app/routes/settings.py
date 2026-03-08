from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..auth import get_current_user
from ..csrf import csrf_protect
from ..db import get_db, get_user_settings

router = APIRouter()


def _t(request: Request):
    return request.app.state.templates


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    settings = get_user_settings(user["id"])
    return _t(request).TemplateResponse(request, "settings.html", {
        "active_tab": "settings", "current_user": user, "settings": settings,
    })


@router.post("/settings/update")
async def update_settings(
    request: Request,
    _csrf: None = Depends(csrf_protect),
    business_name: str = Form(""),
    business_tagline: str = Form(""),
    business_address: str = Form(""),
    business_phone: str = Form(""),
    business_email: str = Form(""),
    currency: str = Form("$"),
    terms_default: str = Form(""),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO user_settings (user_id, business_name, business_tagline, business_address, "
            "business_phone, business_email, currency, terms_default) VALUES (?,?,?,?,?,?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET business_name=excluded.business_name, "
            "business_tagline=excluded.business_tagline, business_address=excluded.business_address, "
            "business_phone=excluded.business_phone, business_email=excluded.business_email, "
            "currency=excluded.currency, terms_default=excluded.terms_default",
            (user["id"], business_name.strip(), business_tagline.strip(), business_address.strip(),
             business_phone.strip(), business_email.strip(), currency.strip() or "$",
             terms_default.strip()),
        )
    return RedirectResponse("/settings", status_code=303)
