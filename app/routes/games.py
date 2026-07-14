from __future__ import annotations
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select, func, desc
import json
import os

from app.config import AsyncSessionLocal, GAMES_DIR
from app.models.score import Score
from app.models.site_settings import GameModule
from app.models.user import User
from app.services.game_loader import get_game_module_info, list_game_modules
from app.routes.auth import verify_token

router = APIRouter()


async def get_current_user(request: Request) -> User | None:
    token = request.cookies.get("token")
    if not token:
        return None
    payload = verify_token(token)
    if not payload or payload.get("scope") != "access":
        return None
    user_id = int(payload["sub"])
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user and user.is_banned:
            return None
        return user


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    from app.main import templates
    user = await get_current_user(request)
    modules = list_game_modules()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "games": modules,
    })


@router.get("/play/{game_id}", response_class=HTMLResponse)
async def play_game(request: Request, game_id: str):
    from app.main import templates
    user = await get_current_user(request)

    info = get_game_module_info(game_id)
    if not info:
        raise HTTPException(status_code=404, detail="游戏不存在")

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(GameModule).where(GameModule.game_id == game_id, GameModule.enabled == True)
        )
        db_module = result.scalar_one_or_none()
        if not db_module:
            raise HTTPException(status_code=404, detail="游戏已下线")

        if game_id == "muyu":
            subq_m = (select(Score.user_id, func.max(Score.score).label("best"))
                      .where(Score.game_id == "muyu").group_by(Score.user_id).subquery())
            rows = (await db.execute(
                select(subq_m.c.user_id, subq_m.c.best, User.username)
                .join(User, subq_m.c.user_id == User.id).where(User.is_banned == False)
            )).all()
            all_s = (await db.execute(select(Score).where(Score.game_id == "muyu"))).scalars().all()
            sm = {}
            for s in all_s:
                if s.user_id not in sm or s.score > sm[s.user_id][0]:
                    gd = s.game_data or {}
                    sm[s.user_id] = (s.score, gd.get("meritComplete", False), gd.get("completedAt", ""))
            def mk(r):
                _, mc, ct = sm.get(r.user_id, (0, False, ""))
                if mc: return (0, ct)
                return (1, -r.best)
            sr = sorted(rows, key=mk)[:10]
            leaderboard = []
            for i, r in enumerate(sr):
                _, mc, _ = sm.get(r.user_id, (0, False, ""))
                leaderboard.append({"rank": i+1, "username": r.username,
                    "score_display": "功德圆满" if mc else str(r.best), "score": r.best})
        else:
            subq = (
                select(Score.user_id, func.max(Score.score).label("best"))
                .where(Score.game_id == game_id)
                .group_by(Score.user_id)
                .subquery()
            )
            scores = await db.execute(
                select(subq.c.best, User.username)
                .join(User, subq.c.user_id == User.id)
                .where(User.is_banned == False)
                .order_by(desc(subq.c.best))
                .limit(10)
            )
            leaderboard = [
                {"rank": i + 1, "username": row.username, "score_display": str(row.best), "score": row.best}
                for i, row in enumerate(scores.all())
            ]

    game_template_path = f"{game_id}/template.html"

    game_html = ""
    tmpl_path = os.path.join(GAMES_DIR, game_template_path)
    if os.path.exists(tmpl_path):
        with open(tmpl_path, "r", encoding="utf-8-sig") as f:
            game_html = f.read()

    my_score = None
    my_rank = None
    if user:
        if game_id == "muyu":
            mq = (await db.execute(
                select(func.max(Score.score)).where(Score.user_id == user.id, Score.game_id == "muyu")
            )).scalar()
            if mq:
                my_score = mq
                mq_full = (await db.execute(
                    select(Score).where(Score.user_id == user.id, Score.game_id == "muyu", Score.score == mq)
                    .limit(1)
                )).scalars().first()
                if mq_full:
                    gd = mq_full.game_data or {}
                    if gd.get("meritComplete"): my_score = "功德圆满"
                # Calculate muyu rank by counting users with higher score in sorted list
                better = 0
                for i, r in enumerate(sr):
                    if r.user_id == user.id:
                        my_rank = i + 1
                        break
        else:
            mq = (await db.execute(
                select(func.max(Score.score)).where(Score.user_id == user.id, Score.game_id == game_id)
            )).scalar()
            if mq:
                my_score = mq
                subq2 = (
                    select(Score.user_id, func.max(Score.score).label("best"))
                    .where(Score.game_id == game_id).group_by(Score.user_id).subquery()
                )
                better = (await db.execute(
                    select(func.count()).select_from(subq2).where(subq2.c.best > mq)
                )).scalar()
                my_rank = better + 1
    total_players = len(rows) if game_id == "muyu" else (await db.execute(select(func.count(func.distinct(Score.user_id))).where(Score.game_id == game_id))).scalar()

    return templates.TemplateResponse("game.html", {
        "request": request,
        "user": user,
        "game": info,
        "game_html": game_html,
        "leaderboard": leaderboard,
        "my_score": my_score,
        "my_rank": my_rank,
        "total_players": total_players,
    })


@router.post("/api/games/{game_id}/score")
async def submit_score(request: Request, game_id: str):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")

    body = await request.json()
    score_value = body.get("score", 0)
    game_data = body.get("game_data", None)

    if not isinstance(score_value, (int, float)) or score_value < 0:
        raise HTTPException(status_code=400, detail="无效的分数")

    score_value = int(score_value)

    async with AsyncSessionLocal() as db:
        module_result = await db.execute(
            select(GameModule).where(GameModule.game_id == game_id, GameModule.enabled == True)
        )
        if not module_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="游戏不存在或已下线")

        is_muyu_accumulate = game_id == "muyu" and game_data and game_data.get("accumulated")

        if is_muyu_accumulate:
            existing = (await db.execute(
                select(Score).where(Score.user_id == user.id, Score.game_id == game_id)
                .order_by(desc(Score.score)).limit(1)
            )).scalars().first()
            if existing:
                old_gd = existing.game_data or {}
                was_merit = old_gd.get("meritComplete", False)
                if was_merit and not game_data.get("meritComplete"):
                    game_data["meritComplete"] = True
                    game_data["completedAt"] = old_gd.get("completedAt")
                existing.score = max(existing.score, score_value)
                existing.game_data = game_data
                score = existing
            else:
                score = Score(user_id=user.id, game_id=game_id, score=score_value, game_data=game_data)
                db.add(score)
        else:
            score = Score(user_id=user.id, game_id=game_id, score=score_value, game_data=game_data)
            db.add(score)

        await db.commit()
        await db.refresh(score)

    import redis.asyncio as aioredis
    from app.config import REDIS_URL
    try:
        r = aioredis.from_url(REDIS_URL)
        await r.publish("leaderboard:update", json.dumps({
            "user_id": user.id,
            "username": user.username,
            "game_id": game_id,
            "score": score_value,
            "score_id": score.id,
        }))
        await r.close()
    except Exception:
        pass

    rank_result = None
    async with AsyncSessionLocal() as db:
        sub = (
            select(Score)
            .where(Score.game_id == game_id, Score.score > score_value)
        )
        count_result = await db.execute(
            select(func.count()).select_from(Score).where(Score.game_id == game_id)
        )
        total = count_result.scalar()
        count_result = await db.execute(
            select(func.count()).select_from(sub.subquery())
        )
        better = count_result.scalar()
        rank_result = better + 1

    return JSONResponse({
        "success": True,
        "score_id": score.id,
        "rank": rank_result,
        "total_players": total,
    })


@router.get("/api/games/muyu/load")
async def load_muyu_score(request: Request):
    user = await get_current_user(request)
    if not user:
        return JSONResponse({"accumulated_score": 0, "max_combo": 0, "total_clicks": 0, "merit_complete": False})

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Score).where(Score.user_id == user.id, Score.game_id == "muyu")
            .order_by(desc(Score.score)).limit(1)
        )
        best = result.scalars().first()
        if best:
            gd = best.game_data or {}
            return JSONResponse({
                "accumulated_score": best.score,
                "max_combo": gd.get("maxCombo", 0),
                "total_clicks": gd.get("clicks", 0),
                "merit_complete": gd.get("meritComplete", False),
                "completed_at": gd.get("completedAt"),
            })
    return JSONResponse({"accumulated_score": 0, "max_combo": 0, "total_clicks": 0, "merit_complete": False})


@router.get("/api/games/{game_id}/leaderboard")
async def game_leaderboard_api(game_id: str, limit: int = 50, offset: int = 0):
    async with AsyncSessionLocal() as db:
        if game_id == "muyu":
            subq_m = (select(Score.user_id, func.max(Score.score).label("best"))
                      .where(Score.game_id == "muyu").group_by(Score.user_id).subquery())
            rows = (await db.execute(
                select(subq_m.c.user_id, subq_m.c.best, User.username)
                .join(User, subq_m.c.user_id == User.id).where(User.is_banned == False)
            )).all()
            all_s = (await db.execute(select(Score).where(Score.game_id == "muyu"))).scalars().all()
            sm = {}
            for s in all_s:
                if s.user_id not in sm or s.score > sm[s.user_id][0]:
                    gd = s.game_data or {}
                    sm[s.user_id] = (s.score, gd.get("meritComplete", False), gd.get("completedAt", ""))
            def mk(r):
                _, mc, ct = sm.get(r.user_id, (0, False, ""))
                if mc: return (0, ct)
                return (1, -r.best)
            sr = sorted(rows, key=mk)
            total = len(sr)
            if offset: sr = sr[offset:]
            if limit > 0: sr = sr[:limit]
            data = [{"rank": offset + i + 1, "username": r.username,
                "score_display": "功德圆满" if sm.get(r.user_id, (0,False,""))[1] else str(r.best),
                "score": r.best} for i, r in enumerate(sr)]
        else:
            subq = (select(Score.user_id, func.max(Score.score).label("best"))
                    .where(Score.game_id == game_id).group_by(Score.user_id).subquery())
            q = select(subq.c.best, User.username).join(User, subq.c.user_id == User.id).where(User.is_banned == False).order_by(desc(subq.c.best))
            if limit > 0: q = q.limit(limit)
            rows = (await db.execute(q)).all()
            data = [{"rank": i+1, "username": row.username, "score_display": str(row.best), "score": row.best} for i, row in enumerate(rows)]
        return {"rows": data}
