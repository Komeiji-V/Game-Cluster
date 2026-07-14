import json
import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select, desc

from app.config import REDIS_URL, AsyncSessionLocal
from app.models.score import Score
from app.models.user import User

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: dict):
        text = json.dumps(message)
        for ws in self.active:
            try:
                await ws.send_text(text)
            except Exception:
                self.active.remove(ws)


manager = ConnectionManager()


@router.websocket("/ws/leaderboard")
async def leaderboard_ws(websocket: WebSocket):
    await manager.connect(websocket)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Score, User.username)
            .join(User, Score.user_id == User.id)
            .where(User.is_banned == False)
            .order_by(desc(Score.score))
            .limit(50)
        )
        rows = result.all()
        snapshot = [
            {"rank": i + 1, "username": row.username, "game_id": row.Score.game_id, "score": row.Score.score}
            for i, row in enumerate(rows)
        ]
        await websocket.send_text(json.dumps({"type": "snapshot", "data": snapshot}))

    try:
        r = aioredis.from_url(REDIS_URL)
        pubsub = r.pubsub()
        await pubsub.subscribe("leaderboard:update")

        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await manager.broadcast({"type": "update", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
    finally:
        manager.disconnect(websocket)
        try:
            await pubsub.unsubscribe("leaderboard:update")
            await r.close()
        except Exception:
            pass
