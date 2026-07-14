from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select, func, desc

from app.config import AsyncSessionLocal
from app.models.score import Score
from app.models.user import User
from app.models.site_settings import GameModule
from app.routes.games import get_current_user

router = APIRouter()


@router.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_page(request: Request, game_id: str = None, search: str = "", rank_jump: str = "", offset: str = "", format: str = ""):
    from app.main import templates
    user = await get_current_user(request)
    rj = int(rank_jump) if rank_jump.isdigit() else 0
    off = int(offset) if offset.isdigit() else 0
    if off > 0: rj = 0

    async with AsyncSessionLocal() as db:
        modules_result = await db.execute(select(GameModule).where(GameModule.enabled == True))
        modules = modules_result.scalars().all()
        my_rank = None; my_score = None

        if game_id == "muyu":
            subq = (select(Score.user_id, func.max(Score.score).label("best"))
                    .where(Score.game_id == "muyu").group_by(Score.user_id).subquery())
            rows = (await db.execute(select(subq.c.user_id, subq.c.best, User.username)
                    .join(User, subq.c.user_id == User.id).where(User.is_banned == False))).all()
            all_scores = (await db.execute(select(Score).where(Score.game_id == "muyu"))).scalars().all()
            score_map = {}
            for s in all_scores:
                if s.user_id not in score_map or s.score > score_map[s.user_id][0]:
                    gd = s.game_data or {}
                    score_map[s.user_id] = (s.score, gd.get("meritComplete", False), gd.get("completedAt", ""))
            def muyu_key(row):
                _, mc, ct = score_map.get(row.user_id, (0, False, ""))
                if mc: return (0, ct)
                return (1, -row.best)
            sorted_rows = sorted(rows, key=muyu_key)
            full_sorted = sorted_rows[:]

            if search:
                found_idx = None
                for i, r in enumerate(full_sorted):
                    if search.lower() in r.username.lower():
                        found_idx = i + 1; break
                if found_idx: rj = found_idx; search = ""

            if rj > 0:
                s = max(0, rj - 6); sorted_rows = full_sorted[s:s+11]
            elif off > 0:
                sorted_rows = full_sorted[off:off+50]
            else:
                sorted_rows = full_sorted[:50]
            leaderboard = []
            for i, row in enumerate(sorted_rows):
                idx = (rj > 0 and max(0, rj - 6) + i + 1) or (off + i + 1)
                _, mc, _ = score_map.get(row.user_id, (0, False, ""))
                entry = {"rank": idx, "username": row.username,
                    "score_display": "功德圆满" if mc else str(row.best), "score": row.best}
                if user and row.user_id == user.id:
                    entry["is_me"] = True; my_rank = idx; my_score = row.best
                leaderboard.append(entry)

            if user and my_rank is None and not rj and not off and not search:
                for i, row in enumerate(full_sorted):
                    if row.user_id == user.id:
                        my_rank = i + 1
                        _, mc, _ = score_map.get(user.id, (0, False, ""))
                        my_score = "功德圆满" if mc else row.best
                        break

        elif game_id:
            subq = (select(Score.user_id, func.max(Score.score).label("best"))
                    .where(Score.game_id == game_id).group_by(Score.user_id).subquery())

            if search:
                found = (await db.execute(
                    select(subq.c.best, subq.c.user_id).join(User, subq.c.user_id == User.id)
                    .where(User.is_banned == False, User.username.ilike(f"%{search}%"))
                    .order_by(desc(subq.c.best)).limit(1)
                )).first()
                if found:
                    better = (await db.execute(
                        select(func.count()).select_from(subq).where(subq.c.best > found.best)
                    )).scalar()
                    rj = better + 1; search = ""

            if rj > 0:
                q = select(subq.c.best, User.username, subq.c.user_id).join(User, subq.c.user_id == User.id).where(User.is_banned == False).order_by(desc(subq.c.best)).offset(max(0, rj - 6)).limit(11)
            elif off > 0:
                q = select(subq.c.best, User.username, subq.c.user_id).join(User, subq.c.user_id == User.id).where(User.is_banned == False).order_by(desc(subq.c.best)).offset(off).limit(50)
            else:
                q = select(subq.c.best, User.username, subq.c.user_id).join(User, subq.c.user_id == User.id).where(User.is_banned == False).order_by(desc(subq.c.best)).limit(50)
            scores = await db.execute(q)
            leaderboard = []
            for i, row in enumerate(scores.all()):
                r = (rj > 0 and max(0, rj - 6) + i + 1) or (off + i + 1)
                entry = {"rank": r, "username": row.username, "score_display": str(row.best), "score": row.best}
                if user and row.user_id == user.id:
                    entry["is_me"] = True; my_rank = r; my_score = row.best
                leaderboard.append(entry)

            if user and my_rank is None and not rj and not off and not search:
                found = (await db.execute(
                    select(subq.c.best).where(subq.c.user_id == user.id)
                )).scalar_one_or_none()
                if found:
                    better = (await db.execute(
                        select(func.count()).select_from(subq).where(subq.c.best > found)
                    )).scalar()
                    my_rank = better + 1; my_score = found

        else:
            subq2 = (select(Score.user_id, func.max(Score.score).label("max_score"))
                     .where(Score.game_id != "muyu").group_by(Score.user_id).subquery())

            if search:
                found = (await db.execute(
                    select(subq2.c.max_score, subq2.c.user_id).join(User, subq2.c.user_id == User.id)
                    .where(User.is_banned == False, User.username.ilike(f"%{search}%"))
                    .order_by(desc(subq2.c.max_score)).limit(1)
                )).first()
                if found:
                    better = (await db.execute(
                        select(func.count()).select_from(subq2).where(subq2.c.max_score > found.max_score)
                    )).scalar()
                    rj = better + 1; search = ""

            if rj > 0:
                q = select(subq2.c.user_id, subq2.c.max_score, User.username).join(User, subq2.c.user_id == User.id).where(User.is_banned == False).order_by(desc(subq2.c.max_score)).offset(max(0, rj - 6)).limit(11)
            elif off > 0:
                q = select(subq2.c.user_id, subq2.c.max_score, User.username).join(User, subq2.c.user_id == User.id).where(User.is_banned == False).order_by(desc(subq2.c.max_score)).offset(off).limit(50)
            else:
                q = select(subq2.c.user_id, subq2.c.max_score, User.username).join(User, subq2.c.user_id == User.id).where(User.is_banned == False).order_by(desc(subq2.c.max_score)).limit(50)
            scores = await db.execute(q)
            leaderboard = []
            for i, row in enumerate(scores.all()):
                r = (rj > 0 and max(0, rj - 6) + i + 1) or (off + i + 1)
                entry = {"rank": r, "username": row.username, "score_display": str(row.max_score), "score": row.max_score}
                if user and row.user_id == user.id:
                    entry["is_me"] = True; my_rank = r; my_score = row.max_score
                leaderboard.append(entry)

            if user and my_rank is None and not rj and not off and not search:
                found = (await db.execute(
                    select(subq2.c.max_score).where(subq2.c.user_id == user.id)
                )).scalar_one_or_none()
                if found:
                    better = (await db.execute(
                        select(func.count()).select_from(subq2).where(subq2.c.max_score > found)
                    )).scalar()
                    my_rank = better + 1; my_score = found

    if format == "json":
        return JSONResponse({"rows": leaderboard})

    return templates.TemplateResponse("leaderboard.html", {
        "request": request, "user": user, "leaderboard": leaderboard,
        "games": modules, "current_game_id": game_id or "",
        "search": search, "rank_jump": rj, "my_rank": my_rank, "my_score": my_score,
    })
