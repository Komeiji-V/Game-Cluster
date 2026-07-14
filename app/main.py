from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from contextlib import asynccontextmanager
import os

from app.config import AsyncSessionLocal, engine, TEMPLATES_DIR, STATIC_DIR, GAMES_DIR, DEFAULT_SITE_TITLE, DEFAULT_SITE_SUBTITLE
from app.models import Base
from app.models.site_settings import SiteSettings

templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.cache = None
templates.env.auto_reload = True


async def load_site_settings() -> dict:
    settings = {
        "site_title": DEFAULT_SITE_TITLE,
        "site_subtitle": DEFAULT_SITE_SUBTITLE,
    }
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(SiteSettings).where(SiteSettings.setting_key.in_(SiteSettings.SITE_KEYS))
            )
            for row in result.scalars().all():
                settings[row.setting_key] = row.value
    except Exception:
        pass
    return settings


@asynccontextmanager
async def lifespan(application: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    from app.services.game_loader import scan_game_modules
    await scan_game_modules()
    settings = await load_site_settings()
    templates.env.globals["config"] = settings
    yield
    await engine.dispose()


app = FastAPI(title="小游戏集群", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

games_static = os.path.join(GAMES_DIR)
if os.path.exists(games_static):
    app.mount("/games/static", StaticFiles(directory=games_static), name="games_static")


@app.middleware("http")
async def site_settings_middleware(request: Request, call_next):
    settings = await load_site_settings()
    templates.env.globals["config"] = settings
    response = await call_next(request)
    return response


from app.routes import auth, games, leaderboard, admin, profile
from app.routes.api import score_query
from app.ws import leaderboard as ws_leaderboard

app.include_router(auth.router)
app.include_router(games.router)
app.include_router(leaderboard.router)
app.include_router(admin.router)
app.include_router(profile.router)
app.include_router(score_query.router)
app.include_router(ws_leaderboard.router)
