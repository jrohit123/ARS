from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from database.db import get_user_by_username, verify_password
from utils.templates import get_templates

router = APIRouter()
templates = get_templates()

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse(request, "login.html", {"error": None})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = get_user_by_username(username)
    if not user or not verify_password(password, user["password_hash"]):
        return templates.TemplateResponse(request, "login.html", {
            "error": "Invalid username or password"
        })
    if not user["is_active"]:
        return templates.TemplateResponse(request, "login.html", {
            "error": "Your account has been deactivated. Contact admin."
        })
    request.session["user_id"] = user["id"]
    request.session["user_role"] = user["role"]
    request.session["user_name"] = user["full_name"]
    return RedirectResponse(url="/dashboard", status_code=302)

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")
