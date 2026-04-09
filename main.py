from fastapi import FastAPI, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn
import traceback
from pathlib import Path

from database.db import init_db
from routers import auth, consignment, admin

app = FastAPI(title="ARS Consignment System")

# Session middleware
app.add_middleware(SessionMiddleware, secret_key="ARS-SECRET-CHANGE-IN-PROD-2025")

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Routers
app.include_router(auth.router)
app.include_router(consignment.router)
app.include_router(admin.router)

# Global exception handler for debugging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"[GLOBAL ERROR] {type(exc).__name__}: {str(exc)}")
    print(f"[GLOBAL ERROR] Traceback:")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal error: {type(exc).__name__}: {str(exc)}"}
    )

@app.on_event("startup")
async def startup():
    init_db()

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard")
    return RedirectResponse(url="/login")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
