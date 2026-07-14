from __future__ import annotations
import os
import json
from sqlalchemy import select
from app.config import GAMES_DIR, AsyncSessionLocal
from app.models.site_settings import GameModule


async def scan_game_modules():
    if not os.path.exists(GAMES_DIR):
        return

    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(GameModule))
        existing_ids = {g.game_id for g in existing.scalars().all()}

        for entry in os.listdir(GAMES_DIR):
            module_path = os.path.join(GAMES_DIR, entry)
            if not os.path.isdir(module_path) or entry.startswith("_"):
                continue

            manifest_path = os.path.join(module_path, "manifest.json")
            if not os.path.exists(manifest_path):
                continue

            try:
                with open(manifest_path, "r", encoding="utf-8-sig") as f:
                    manifest = json.load(f)
            except (json.JSONDecodeError, IOError):
                continue

            game_id = manifest.get("game_id", entry)
            if game_id in existing_ids:
                continue

            module = GameModule(
                game_id=game_id,
                name=manifest.get("name", game_id),
                description=manifest.get("description", ""),
                version=manifest.get("version", "1.0"),
                author=manifest.get("author", "unknown"),
                enabled=True,
            )
            db.add(module)
            existing_ids.add(game_id)

        await db.commit()


def get_game_module_info(game_id: str) -> dict | None:
    module_path = os.path.join(GAMES_DIR, game_id)
    manifest_path = os.path.join(module_path, "manifest.json")
    if not os.path.exists(manifest_path):
        return None
    with open(manifest_path, "r", encoding="utf-8-sig") as f:
        manifest = json.load(f)
    manifest["_path"] = module_path
    manifest["has_static"] = os.path.isdir(os.path.join(module_path, "static"))
    return manifest


def list_game_modules() -> list[dict]:
    if not os.path.exists(GAMES_DIR):
        return []
    modules = []
    for entry in os.listdir(GAMES_DIR):
        if entry.startswith("_") or entry.startswith("."):
            continue
        info = get_game_module_info(entry)
        if info:
            modules.append(info)
    return modules


def validate_game_zip(extract_path: str) -> tuple[bool, str]:
    manifest = os.path.join(extract_path, "manifest.json")
    game_js = os.path.join(extract_path, "static", "game.js")
    template = os.path.join(extract_path, "template.html")

    if not os.path.exists(manifest):
        return False, "缺少 manifest.json"
    if not os.path.exists(game_js):
        return False, "缺少 static/game.js"
    if not os.path.exists(template):
        return False, "缺少 template.html"

    try:
        with open(manifest, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        if "game_id" not in data:
            return False, "manifest.json 缺少 game_id"
        if not data["game_id"].isidentifier():
            return False, "game_id 必须是合法的标识符"
    except (json.JSONDecodeError, IOError):
        return False, "manifest.json 格式无效"

    return True, ""
