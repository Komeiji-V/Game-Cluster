import os
import json
import shutil
import zipfile
from fastapi import APIRouter, Request, Form, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select, func, delete

from app.config import AsyncSessionLocal, GAMES_DIR, UPLOADS_DIR
from app.models.user import User
from app.models.score import Score
from app.models.site_settings import SiteSettings, GameModule
from app.routes.auth import verify_token
from app.services.game_loader import validate_game_zip
from app.services.auth_service import hash_password

router = APIRouter(prefix="/admin")


async def require_admin(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    payload = verify_token(token)
    if not payload or payload.get("scope") != "access":
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    user_id = int(payload["sub"])
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.is_admin:
            raise HTTPException(status_code=302, headers={"Location": "/"})
    return user


@router.get("", response_class=HTMLResponse)
async def admin_dashboard(request: Request, admin: User = Depends(require_admin)):
    from app.main import templates
    async with AsyncSessionLocal() as db:
        total_users = (await db.execute(select(func.count()).select_from(User))).scalar()
        total_games = (await db.execute(
            select(func.count()).select_from(GameModule)
        )).scalar()
        total_scores = (await db.execute(select(func.count()).select_from(Score))).scalar()
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "user": admin,
        "total_users": total_users,
        "total_games": total_games,
        "total_scores": total_scores,
    })


@router.get("/smtp", response_class=HTMLResponse)
async def admin_smtp(request: Request, admin: User = Depends(require_admin)):
    from app.main import templates
    async with AsyncSessionLocal() as db:
        keys = SiteSettings.SMTP_KEYS
        result = await db.execute(
            select(SiteSettings).where(SiteSettings.setting_key.in_(keys))
        )
        config = {r.setting_key: r.value for r in result.scalars().all()}
    return templates.TemplateResponse("admin/smtp.html", {
        "request": request,
        "user": admin,
        "config": config,
    })


@router.post("/smtp")
async def admin_smtp_save(
    request: Request,
    admin: User = Depends(require_admin),
    smtp_host: str = Form(""),
    smtp_port: str = Form("587"),
    smtp_username: str = Form(""),
    smtp_password: str = Form(""),
    smtp_from_email: str = Form(""),
    smtp_from_name: str = Form(""),
    smtp_use_tls: str = Form("true"),
):
    from app.main import templates
    data = {
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "smtp_username": smtp_username,
        "smtp_password": smtp_password,
        "smtp_from_email": smtp_from_email,
        "smtp_from_name": smtp_from_name,
        "smtp_use_tls": smtp_use_tls,
    }
    async with AsyncSessionLocal() as db:
        for key, value in data.items():
            existing = (await db.execute(
                select(SiteSettings).where(SiteSettings.setting_key == key)
            )).scalar_one_or_none()
            if existing:
                existing.value = value
            else:
                db.add(SiteSettings(setting_key=key, value=value))
        await db.commit()

    return templates.TemplateResponse("admin/smtp.html", {
        "request": request,
        "user": admin,
        "config": data,
        "success": "SMTP 设置已保存",
    })


@router.get("/games", response_class=HTMLResponse)
async def admin_games(request: Request, admin: User = Depends(require_admin)):
    from app.main import templates
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(GameModule))
        modules = result.scalars().all()
    return templates.TemplateResponse("admin/games.html", {
        "request": request,
        "user": admin,
        "modules": modules,
    })


@router.post("/games/upload")
async def admin_games_upload(
    request: Request,
    admin: User = Depends(require_admin),
    file: UploadFile = File(...),
):
    if not file.filename or not file.filename.endswith(".zip"):
            raise HTTPException(status_code=400, detail="仅支持 .zip 文件")

    temp_dir = os.path.join(GAMES_DIR, "_upload_temp")
    os.makedirs(temp_dir, exist_ok=True)
    safe_name = os.path.basename(file.filename)
    zip_path = os.path.join(temp_dir, safe_name)

    with open(zip_path, "wb") as f:
        content = await file.read()
        f.write(content)

    extract_path = os.path.join(temp_dir, "extracted")
    if os.path.exists(extract_path):
        shutil.rmtree(extract_path)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.infolist():
                member_path = os.path.normpath(os.path.join(extract_path, member.filename))
                if not member_path.startswith(os.path.normpath(extract_path) + os.sep):
                    raise HTTPException(status_code=400, detail="压缩包包含非法路径")
            zf.extractall(extract_path)

        valid, error = validate_game_zip(extract_path)
        if not valid:
            raise HTTPException(status_code=400, detail=error)

        with open(os.path.join(extract_path, "manifest.json"), "r", encoding="utf-8-sig") as f:
            manifest = json.load(f)
        game_id = manifest["game_id"]

        dest = os.path.join(GAMES_DIR, game_id)
        if os.path.exists(dest):
            raise HTTPException(status_code=400, detail=f"游戏 '{game_id}' 已存在")

        shutil.move(extract_path, dest)

        async with AsyncSessionLocal() as db:
            existing = (await db.execute(
                select(GameModule).where(GameModule.game_id == game_id)
            )).scalar_one_or_none()
            if not existing:
                module = GameModule(
                    game_id=game_id,
                    name=manifest.get("name", game_id),
                    description=manifest.get("description", ""),
                    version=manifest.get("version", "1.0"),
                    author=manifest.get("author", "unknown"),
                )
                db.add(module)
            await db.commit()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path)

    return RedirectResponse("/admin/games", status_code=303)


@router.post("/games/{game_id}/toggle")
async def admin_games_toggle(game_id: str, admin: User = Depends(require_admin)):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(GameModule).where(GameModule.game_id == game_id))
        module = result.scalar_one_or_none()
        if module:
            module.enabled = not module.enabled
            await db.commit()
    return RedirectResponse("/admin/games", status_code=303)


@router.post("/games/{game_id}/delete")
async def admin_games_delete(game_id: str, admin: User = Depends(require_admin)):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(GameModule).where(GameModule.game_id == game_id))
        module = result.scalar_one_or_none()
        if module:
            await db.execute(delete(Score).where(Score.game_id == game_id))
            await db.delete(module)
            await db.commit()

    module_path = os.path.join(GAMES_DIR, game_id)
    if os.path.exists(module_path):
        shutil.rmtree(module_path)

    return RedirectResponse("/admin/games", status_code=303)


@router.get("/players", response_class=HTMLResponse)
async def admin_players(
    request: Request,
    admin: User = Depends(require_admin),
    search: str = "",
    page: int = 1,
):
    from app.main import templates
    per_page = 20
    offset = (page - 1) * per_page

    async with AsyncSessionLocal() as db:
        if search:
            result = await db.execute(
                select(User).where(
                    (User.username.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%"))
                ).order_by(User.id).offset(offset).limit(per_page)
            )
            total = (await db.execute(
                select(func.count()).select_from(User).where(
                    (User.username.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%"))
                )
            )).scalar()
        else:
            result = await db.execute(
                select(User).order_by(User.id).offset(offset).limit(per_page)
            )
            total = (await db.execute(select(func.count()).select_from(User))).scalar()

        players = result.scalars().all()

    total_pages = max(1, (total + per_page - 1) // per_page)

    return templates.TemplateResponse("admin/players.html", {
        "request": request,
        "user": admin,
        "players": players,
        "search": search,
        "page": page,
        "total_pages": total_pages,
        "total": total,
    })


@router.post("/players/{player_id}/edit")
async def admin_players_edit(
    player_id: int,
    admin: User = Depends(require_admin),
    username: str = Form(None),
    email: str = Form(None),
    password: str = Form(None),
    is_banned: str = Form(None),
    is_admin_val: str = Form(None),
):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == player_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="玩家不存在")

        if username and username != user.username:
            existing = (await db.execute(
                select(User).where(User.username == username)
            )).scalar_one_or_none()
            if existing:
                raise HTTPException(status_code=400, detail="用户名已被占用")
            user.username = username

        if email and email != user.email:
            existing = (await db.execute(
                select(User).where(User.email == email)
            )).scalar_one_or_none()
            if existing:
                raise HTTPException(status_code=400, detail="邮箱已被占用")
            user.email = email

        if password:
            user.password_hash = hash_password(password)

        if is_banned is not None:
            user.is_banned = is_banned == "1"

        if is_admin_val is not None:
            user.is_admin = is_admin_val == "1"

        await db.commit()

    return RedirectResponse("/admin/players", status_code=303)


@router.get("/settings", response_class=HTMLResponse)
async def admin_settings(request: Request, admin: User = Depends(require_admin)):
    from app.main import templates
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SiteSettings).where(SiteSettings.setting_key.in_(SiteSettings.SITE_KEYS))
        )
        config = {r.setting_key: r.value for r in result.scalars().all()}
    return templates.TemplateResponse("admin/site_settings.html", {
        "request": request,
        "user": admin,
        "config": config,
    })


@router.post("/settings")
async def admin_settings_save(
    admin: User = Depends(require_admin),
    site_title: str = Form(""),
    site_subtitle: str = Form(""),
    site_primary_color: str = Form("#f97316"),
    site_bg_color: str = Form("#ffffff"),
    site_base_url: str = Form(""),
):
    data = {
        "site_title": site_title,
        "site_subtitle": site_subtitle,
        "site_primary_color": site_primary_color,
        "site_bg_color": site_bg_color,
        "site_base_url": site_base_url,
    }
    async with AsyncSessionLocal() as db:
        for key, value in data.items():
            existing = (await db.execute(
                select(SiteSettings).where(SiteSettings.setting_key == key)
            )).scalar_one_or_none()
            if existing:
                existing.value = value
            else:
                db.add(SiteSettings(setting_key=key, value=value))
        await db.commit()
    return RedirectResponse("/admin/settings", status_code=303)


@router.post("/settings/upload")
async def admin_settings_upload(
    admin: User = Depends(require_admin),
    file: UploadFile = File(...),
    type: str = Form("wallpaper"),
):
    if type not in ("favicon", "wallpaper"):
        raise HTTPException(status_code=400, detail="无效的类型")

    ext = os.path.splitext(file.filename)[1] if file.filename else ".png"
    filename = "favicon" + ext if type == "favicon" else "wallpaper" + ext
    key = "site_favicon" if type == "favicon" else "site_wallpaper"

    filepath = os.path.join(UPLOADS_DIR, filename)
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    url = f"/static/uploads/{filename}"
    async with AsyncSessionLocal() as db:
        existing = (await db.execute(
            select(SiteSettings).where(SiteSettings.setting_key == key)
        )).scalar_one_or_none()
        if existing:
            existing.value = url
        else:
            db.add(SiteSettings(setting_key=key, value=url))
        await db.commit()

    return RedirectResponse("/admin/settings", status_code=303)
