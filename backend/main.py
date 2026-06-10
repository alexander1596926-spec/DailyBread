import logging
import os
import secrets
import traceback
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.auth import (
    SESSION_COOKIE_NAME,
    STATE_COOKIE_NAME,
    SESSION_MAX_AGE,
    STATE_MAX_AGE,
    build_avatar_url,
    build_guild_icon_url,
    create_session_cookie_value,
    get_login_redirect_url,
    get_session,
    exchange_code_for_token,
    fetch_discord_guilds,
    fetch_discord_user,
)
from backend.config import STATIC_DIR, TEMPLATES_DIR
from backend.routes import router as routes_router
from backend.services import discord_service, supabase_service

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", os.getenv("discord_client_id", ""))


app = FastAPI(title="DailyBread", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(routes_router)

templates = Jinja2Templates(directory=TEMPLATES_DIR)


def build_template_context(request: Request, extra: dict | None = None) -> dict:
    session = get_session(request)
    context = {
        "request": request,
        "user": session["user"] if session else None,
        "discord_client_id": DISCORD_CLIENT_ID,
    }
    if extra:
        context.update(extra)
    return context


def _get_user_guilds_from_db(session: dict) -> list[dict]:
    user_record = supabase_service.get_user_by_discord_id(str(session["user"]["id"]))
    if not user_record:
        return session.get("guilds", [])

    guilds = supabase_service.get_user_guilds(user_record["id"])
    for guild in guilds:
        guild["icon_url"] = build_guild_icon_url({"id": guild.get("guild_id"), "icon": guild.get("icon")})
    return guilds


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "pages/index.html",
        build_template_context(request, {"page_title": "DailyBread", "active_page": "home"}),
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    session = get_session(request)
    if session:
        return RedirectResponse(url="/dashboard")

    return templates.TemplateResponse(
        request,
        "pages/login.html",
        build_template_context(request, {"page_title": "Log in - DailyBread", "active_page": "login"}),
    )


@app.get("/login/discord")
def login_discord(request: Request) -> RedirectResponse:
    state = secrets.token_urlsafe(16)
    redirect_url = get_login_redirect_url(state)
    response = RedirectResponse(url=redirect_url)
    secure_cookie = request.url.scheme == "https"
    response.set_cookie(
        STATE_COOKIE_NAME,
        state,
        max_age=STATE_MAX_AGE,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
    )
    return response


@app.get("/callback")
def oauth_callback(request: Request, code: str | None = None, state: str | None = None) -> RedirectResponse:
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OAuth callback parameters.")

    expected_state = request.cookies.get(STATE_COOKIE_NAME)
    if not expected_state or expected_state != state:
        raise HTTPException(status_code=403, detail="Invalid OAuth state. Please try again.")

    print("OAUTH CALLBACK ENTERED")
    try:
        token_data = exchange_code_for_token(code)
        print("TOKEN EXCHANGE SUCCESS", {k: token_data[k] for k in token_data if k != 'access_token'})
        access_token = token_data["access_token"]

        user_data = fetch_discord_user(access_token)
        print("DISCORD USER FETCHED", {"id": user_data.get("id"), "username": user_data.get("username")})

        guilds_data = fetch_discord_guilds(access_token)
        print("DISCORD GUILDS FETCHED", {"count": len(guilds_data)})

        print("SUPABASE SYNC STARTED")
        user = {
            "id": user_data["id"],
            "username": user_data["username"],
            "avatar": user_data.get("avatar"),
            "avatar_url": build_avatar_url(user_data),
        }

        print("USER UPSERT ATTEMPT", {
            "discord_id": str(user_data["id"]),
            "username": user_data.get("username", ""),
            "avatar": user["avatar"],
            "global_name": user_data.get("global_name", ""),
        })
        user_record = supabase_service.upsert_user_by_discord_id(
            discord_id=str(user_data["id"]),
            username=user_data.get("username", ""),
            avatar=user.get("avatar"),
            global_name=user_data.get("global_name", ""),
        )
        print("USER UPSERT RESPONSE", user_record)

        synced_guilds = []
        for guild in guilds_data:
            guild_id = str(guild.get("id", ""))
            is_owner = guild.get("owner") is True
            permissions = int(guild.get("permissions", 0) or 0)
            is_admin = is_owner or ((permissions & 0x8) == 0x8)

            # FILTER: Only sync guilds where user is owner or admin
            if not is_admin:
                print(f"GUILD SKIPPED (not admin/owner): {guild_id}")
                continue

            print("GUILD UPSERT ATTEMPT", {
                "guild_id": guild_id,
                "name": guild.get("name", ""),
                "icon": guild.get("icon"),
                "owner_id": guild.get("owner_id"),
                "permissions": permissions,
                "is_admin": is_admin,
            })

            has_bot = False
            try:
                has_bot = discord_service.is_bot_in_guild(guild_id)
                print(f"BOT DETECTION for guild {guild_id}: has_bot={has_bot}")
            except Exception as exc:
                print(f"BOT PRESENCE CHECK FAILED for guild {guild_id}: {exc}")

            db_guild = supabase_service.upsert_guild(
                guild_id=guild_id,
                name=guild.get("name", ""),
                icon=guild.get("icon"),
                owner_id=guild.get("owner_id"),
                permissions=permissions,
                has_bot=has_bot,
            )
            print("GUILD UPSERT RESPONSE", db_guild)

            print("USER_GUILD UPSERT ATTEMPT", {
                "user_id": user_record["id"],
                "guild_id": guild_id,
                "permissions": permissions,
                "is_owner": is_owner,
                "is_admin": is_admin,
            })
            user_guild = supabase_service.ensure_user_guild(
                user_id=user_record["id"],
                guild_id=guild_id,
                permissions=permissions,
                is_owner=is_owner,
                is_admin=is_admin,
            )
            print("USER_GUILD UPSERT RESPONSE", user_guild)

            # Normalized response format
            synced_guilds.append(
                {
                    "guild_id": db_guild["guild_id"],
                    "name": db_guild.get("name"),
                    "icon": db_guild.get("icon"),
                    "icon_url": build_guild_icon_url(db_guild) if db_guild.get("icon") else None,
                    "has_bot": has_bot,
                    "is_owner": is_owner,
                    "is_admin": is_admin,
                }
            )

        print("SUPABASE SYNC COMPLETED")
    except Exception as exc:
        print("OAUTH CALLBACK FAILED", str(exc))
        print(traceback.format_exc())
        raise

    session_value = create_session_cookie_value(user, synced_guilds)
    response = RedirectResponse(url="/dashboard")
    secure_cookie = request.url.scheme == "https"
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_value,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
    )
    response.delete_cookie(STATE_COOKIE_NAME)
    return response


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request) -> HTMLResponse:
    session = get_session(request)
    if not session:
        return RedirectResponse(url="/login")

    guilds = _get_user_guilds_from_db(session)
    return templates.TemplateResponse(
        request,
        "pages/dashboard.html",
        build_template_context(request, {
            "page_title": "Dashboard - DailyBread",
            "active_page": "dashboard",
            "user": session["user"],
            "guilds": guilds,
        }),
    )


@app.get("/dashboard/guild/{guild_id}", response_class=HTMLResponse)
async def guild_management_page(request: Request, guild_id: str) -> HTMLResponse:
    session = get_session(request)
    if not session:
        return RedirectResponse(url="/login")

    guilds = _get_user_guilds_from_db(session)
    guild = next((g for g in guilds if str(g.get("guild_id")) == str(guild_id)), None)
    if not guild:
        return RedirectResponse(url="/dashboard")

    return templates.TemplateResponse(
        request,
        "pages/guild.html",
        build_template_context(request, {
            "page_title": f"Manage {guild['name']} - DailyBread",
            "active_page": "guild",
            "user": session["user"],
            "guild": guild,
        }),
    )


@app.get("/dashboard/guild/{guild_id}/builder", response_class=HTMLResponse)
async def guild_builder_page(request: Request, guild_id: str) -> HTMLResponse:
    session = get_session(request)
    if not session:
        return RedirectResponse(url="/login")

    guilds = _get_user_guilds_from_db(session)
    guild = next((g for g in guilds if str(g.get("guild_id")) == str(guild_id)), None)
    if not guild:
        return RedirectResponse(url="/dashboard")

    return templates.TemplateResponse(
        request,
        "pages/guild-builder.html",
        build_template_context(request, {
            "page_title": f"Embed Builder - {guild['name']} - DailyBread",
            "active_page": "builder",
            "user": session["user"],
            "guild": guild,
        }),
    )


@app.get("/dashboard/builder", response_class=HTMLResponse)
async def builder_page(request: Request) -> HTMLResponse:
    session = get_session(request)
    if not session:
        return RedirectResponse(url="/login")

    guilds = _get_user_guilds_from_db(session)
    return templates.TemplateResponse(
        request,
        "pages/builder.html",
        build_template_context(request, {
            "page_title": "Embed Builder - DailyBread",
            "active_page": "builder",
            "user": session["user"],
            "guilds": guilds,
        }),
    )


@app.get("/logout")
def logout(request: Request) -> RedirectResponse:
    response = RedirectResponse(url="/")
    response.delete_cookie(SESSION_COOKIE_NAME)
    response.delete_cookie(STATE_COOKIE_NAME)
    return response


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
