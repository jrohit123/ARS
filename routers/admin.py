from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from database.db import get_db, hash_password
from utils.templates import get_templates

router = APIRouter(prefix="/admin")
templates = get_templates()

def require_admin(request: Request):
    if not request.session.get("user_id") or request.session.get("user_role") != "admin":
        return False
    return True

@router.get("/users", response_class=HTMLResponse)
async def list_users(request: Request):
    if not require_admin(request):
        return RedirectResponse(url="/dashboard")
    conn = get_db()
    users = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    return templates.TemplateResponse(request, "admin_users.html", {
        "users": users,
        "user_name": request.session.get("user_name"),
        "user_role": request.session.get("user_role"),
        "error": None, "success": None
    })

@router.post("/users/add")
async def add_user(
    request: Request,
    username: str = Form(...),
    full_name: str = Form(...),
    email: str = Form(""),
    password: str = Form(...),
    role: str = Form("staff")
):
    if not require_admin(request):
        return RedirectResponse(url="/dashboard")
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO users (username, password_hash, full_name, email, role)
            VALUES (?, ?, ?, ?, ?)
        """, (username, hash_password(password), full_name, email, role))
        conn.commit()
    except Exception as e:
        conn.close()
        users = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
        return templates.TemplateResponse(request, "admin_users.html", {"users": users,
            "user_name": request.session.get("user_name"),
            "user_role": request.session.get("user_role"),
            "error": f"Could not add user: {str(e)}", "success": None})
    conn.close()
    return RedirectResponse(url="/admin/users?success=1", status_code=302)

@router.post("/users/{user_id}/toggle")
async def toggle_user(request: Request, user_id: int):
    if not require_admin(request):
        return RedirectResponse(url="/dashboard")
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if user:
        new_status = 0 if user["is_active"] else 1
        conn.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_status, user_id))
        conn.commit()
    conn.close()
    return RedirectResponse(url="/admin/users", status_code=302)

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    if not require_admin(request):
        return RedirectResponse(url="/dashboard")
    conn = get_db()
    settings = {row["key"]: row["value"] for row in conn.execute("SELECT * FROM app_settings").fetchall()}
    conn.close()
    return templates.TemplateResponse(request, "admin_settings.html", {
        "settings": settings,
        "user_name": request.session.get("user_name"),
        "user_role": request.session.get("user_role"),
        "success": None, "error": None
    })

@router.post("/settings")
async def save_settings(
    request: Request,
    smtp_host: str = Form(""),
    smtp_port: str = Form("587"),
    smtp_user: str = Form(""),
    smtp_password: str = Form(""),
    smtp_from_name: str = Form("ARS Consignment System"),
    company_name: str = Form("Aggarwal Routemaster Services Pvt. Ltd."),
    company_gstin: str = Form(""),
    company_phone: str = Form(""),
):
    if not require_admin(request):
        return RedirectResponse(url="/dashboard")
    conn = get_db()
    settings = {
        "smtp_host": smtp_host, "smtp_port": smtp_port,
        "smtp_user": smtp_user, "smtp_password": smtp_password,
        "smtp_from_name": smtp_from_name, "company_name": company_name,
        "company_gstin": company_gstin, "company_phone": company_phone
    }
    for key, value in settings.items():
        conn.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()
    return templates.TemplateResponse(request, "admin_settings.html", {
        "settings": settings,
        "user_name": request.session.get("user_name"),
        "user_role": request.session.get("user_role"),
        "success": "Settings saved successfully.", "error": None
    })
