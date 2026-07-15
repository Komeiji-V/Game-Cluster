from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func, desc

from app.config import AsyncSessionLocal
from app.models.score import Score
from app.models.user import User
from app.models.site_settings import SiteSettings, GameModule

router = APIRouter()


@router.get("/api/widget/{game_id}/{user_id}", response_class=HTMLResponse)
async def score_widget(request: Request, game_id: str, user_id: int):
    from app.main import templates

    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not user or user.is_banned:
            return HTMLResponse("<div style='padding:10px;color:#999;font-size:12px;'>未找到用户</div>")

        best = (await db.execute(
            select(Score).where(Score.user_id == user_id, Score.game_id == game_id)
            .order_by(desc(Score.score)).limit(1)
        )).scalar_one_or_none()

        total_plays = (await db.execute(
            select(func.count()).select_from(Score)
            .where(Score.user_id == user_id, Score.game_id == game_id)
        )).scalar()

        if best:
            better_count = (await db.execute(
                select(func.count()).select_from(Score)
                .where(Score.game_id == game_id, Score.score > best.score)
            )).scalar()
            rank = better_count + 1
            total_users = (await db.execute(
                select(func.count(func.distinct(Score.user_id)))
                .where(Score.game_id == game_id)
            )).scalar()
        else:
            rank = None
            total_users = 0

        site_title = "小游戏集群"
        site_base_url = ""
        site_result = await db.execute(
            select(SiteSettings).where(SiteSettings.setting_key.in_(["site_title", "site_base_url"]))
        )
        for row in site_result.scalars().all():
            if row.setting_key == "site_title" and row.value:
                site_title = row.value
            elif row.setting_key == "site_base_url" and row.value:
                site_base_url = row.value.rstrip("/")

        game_name = game_id
        from app.services.game_loader import get_game_module_info
        info = get_game_module_info(game_id)
        if info:
            game_name = info.get("name", game_id)

        theme = request.query_params.get("theme", "light")
        compact = request.query_params.get("compact", "0")
        w = request.query_params.get("w", "")
        h = request.query_params.get("h", "")

    return templates.TemplateResponse("widgets/score_card.html", {
        "request": request,
        "player": user,
        "game_name": game_name,
        "game_id": game_id,
        "site_title": site_title,
        "site_base_url": site_base_url,
        "best_score": best.score if best else 0,
        "rank": rank,
        "total_users": total_users,
        "total_plays": total_plays,
        "theme": theme,
        "compact": compact == "1",
        "w": w,
        "h": h,
    })


@router.get("/api/widget/{game_id}/{user_id}/json")
async def score_widget_json(request: Request, game_id: str, user_id: int):
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not user or user.is_banned:
            return {"error": "用户不存在"}

        best = (await db.execute(
            select(Score).where(Score.user_id == user_id, Score.game_id == game_id)
            .order_by(desc(Score.score)).limit(1)
        )).scalar_one_or_none()

        total_plays = (await db.execute(
            select(func.count()).select_from(Score)
            .where(Score.user_id == user_id, Score.game_id == game_id)
        )).scalar()

        if best:
            better_count = (await db.execute(
                select(func.count()).select_from(Score)
                .where(Score.game_id == game_id, Score.score > best.score)
            )).scalar()
            rank = better_count + 1
            total_users = (await db.execute(
                select(func.count(func.distinct(Score.user_id)))
                .where(Score.game_id == game_id)
            )).scalar()
        else:
            rank = None
            total_users = 0

    return {
        "game_id": game_id,
        "user_id": user_id,
        "username": user.username,
        "best_score": best.score if best else 0,
        "rank": rank,
        "total_users": total_users,
        "total_plays": total_plays,
    }


@router.get("/api/ranking/total/{user_id}")
async def total_ranking_html(request: Request, user_id: int):
    from app.main import templates
    data = await _total_ranking_data(user_id)
    if "error" in data:
        return HTMLResponse("<div style='padding:10px;color:#999;font-size:12px;'>未找到用户</div>")

    theme = request.query_params.get("theme", "light")
    w = request.query_params.get("w", "")
    h = request.query_params.get("h", "")
    total_plays = sum(g.get("plays", 0) for g in data["games"])
    total_str = f"{data['total_score']:,}"

    site_name = "小游戏集群"
    site_base_url = ""
    try:
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(
                select(SiteSettings).where(SiteSettings.setting_key.in_(["site_title", "site_base_url"]))
            )).scalars().all()
            for row in rows:
                if row.setting_key == "site_title" and row.value: site_name = row.value
                elif row.setting_key == "site_base_url" and row.value: site_base_url = row.value.rstrip("/")
    except Exception:
        pass

    return templates.TemplateResponse("widgets/total_card.html", {
        "request": request, "player": {"username": data["username"]},
        "site_name": site_name, "site_base_url": site_base_url, "games": data["games"],
        "total_score_str": total_str, "total_plays": total_plays, "theme": theme,
        "w": w, "h": h,
    })


@router.get("/api/ranking/total/{user_id}/json")
async def total_ranking_json(user_id: int):
    return await _total_ranking_data(user_id)


async def _total_ranking_data(user_id: int) -> dict:
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not user or user.is_banned:
            return {"error": "用户不存在"}

        counting_ids = (await db.execute(
            select(GameModule.game_id).where(GameModule.counts_toward_total == True)
        )).scalars().all()

        subq = (
            select(
                Score.user_id,
                Score.game_id,
                func.max(Score.score).label("best_score"),
                func.count().label("plays"),
                func.max(Score.played_at).label("last_played"),
            )
            .where(Score.user_id == user_id)
            .group_by(Score.user_id, Score.game_id)
            .subquery()
        )
        rows = (await db.execute(select(subq))).all()

        games = []
        total_score = 0
        for row in rows:
            better = (await db.execute(
                select(func.count()).select_from(Score)
                .where(Score.game_id == row.game_id, Score.score > row.best_score)
            )).scalar()
            total = (await db.execute(
                select(func.count(func.distinct(Score.user_id)))
                .where(Score.game_id == row.game_id)
            )).scalar()

            game_name = row.game_id
            from app.services.game_loader import get_game_module_info
            info = get_game_module_info(row.game_id)
            if info:
                game_name = info.get("name", row.game_id)

            games.append({
                "game_id": row.game_id,
                "game_name": game_name,
                "best_score": row.best_score,
                "score_display": str(row.best_score),
                "rank": better + 1,
                "total_users": total,
                "plays": row.plays,
                "last_played": str(row.last_played) if row.last_played else None,
            })
            if row.game_id in counting_ids:
                total_score += row.best_score

        for g in games:
            if g["game_id"] == "muyu":
                full = (await db.execute(
                    select(Score).where(Score.user_id == user_id, Score.game_id == "muyu")
                    .order_by(desc(Score.score)).limit(1)
                )).scalars().first()
                if full:
                    gd = full.game_data or {}
                    if gd.get("meritComplete"):
                        g["score_display"] = "功德圆满"
                break

    return {
        "user_id": user_id,
        "username": user.username,
        "total_score": total_score,
        "games": games,
    }
