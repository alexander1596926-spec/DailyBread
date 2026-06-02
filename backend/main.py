from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.config import STATIC_DIR, TEMPLATES_DIR


app = FastAPI(title="DailyBread", version="0.1.0")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "pages/index.html",
        {"page_title": "DailyBread", "active_page": "home"},
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "pages/login.html",
        {"page_title": "Log in - DailyBread", "active_page": "login"},
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "pages/dashboard.html",
        {"page_title": "Dashboard - DailyBread", "active_page": "dashboard"},
    )


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
