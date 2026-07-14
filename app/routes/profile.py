from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy import select

from app.config import AsyncSessionLocal
from app.models.user import User
from app.routes.games import get_current_user
from app.services.auth_service import verify_password, hash_password, create_access_token, verify_token
from app.services.email_service import send_email_change_verification

router = APIRouter()


async def require_user(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    return user


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, user: User = Depends(require_user)):
    from app.main import templates
    return templates.TemplateResponse("profile.html", {"request": request, "user": user})


@router.post("/profile")
async def profile_save(
    request: Request,
    user: User = Depends(require_user),
    action: str = Form(...),
    username: str = Form(""),
    old_password: str = Form(""),
    new_password: str = Form(""),
    new_password_confirm: str = Form(""),
    new_email: str = Form(""),
):
    from app.main import templates

    if action == "username":
        if not username or len(username) < 3 or len(username) > 32:
            return templates.TemplateResponse("profile.html", {"request": request, "user": user, "error": "用户名需 3-32 个字符"})
        async with AsyncSessionLocal() as db:
            exist = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()
            if exist and exist.id != user.id:
                return templates.TemplateResponse("profile.html", {"request": request, "user": user, "error": "用户名已被占用"})
            user.username = username
            await db.commit()
        return templates.TemplateResponse("profile.html", {"request": request, "user": user, "success": "用户名已修改"})

    elif action == "password":
        if not verify_password(old_password, user.password_hash):
            return templates.TemplateResponse("profile.html", {"request": request, "user": user, "error": "旧密码错误"})
        if len(new_password) < 6:
            return templates.TemplateResponse("profile.html", {"request": request, "user": user, "error": "新密码至少 6 位"})
        if new_password != new_password_confirm:
            return templates.TemplateResponse("profile.html", {"request": request, "user": user, "error": "两次新密码不一致"})
        async with AsyncSessionLocal() as db:
            u = (await db.execute(select(User).where(User.id == user.id))).scalar_one()
            u.password_hash = hash_password(new_password)
            await db.commit()
        return templates.TemplateResponse("profile.html", {"request": request, "user": user, "success": "密码已修改"})

    elif action == "change_email":
        if not new_email or "@" not in new_email:
            return templates.TemplateResponse("profile.html", {"request": request, "user": user, "error": "请输入有效邮箱"})
        async with AsyncSessionLocal() as db:
            exist = (await db.execute(select(User).where(User.email == new_email))).scalar_one_or_none()
            if exist:
                return templates.TemplateResponse("profile.html", {"request": request, "user": user, "error": "该邮箱已被使用"})
        token = create_access_token({"sub": str(user.id), "scope": "change_email", "new_email": new_email})
        base_url = str(request.base_url).rstrip("/")
        verify_url = f"{base_url}/auth/verify-email?token={token}"
        sent = await send_email_change_verification(new_email, user.username, verify_url)
        if sent:
            return templates.TemplateResponse("profile.html", {"request": request, "user": user, "success": "验证邮件已发送到新邮箱，请查收"})
        else:
            return templates.TemplateResponse("profile.html", {"request": request, "user": user, "error": "SMTP 未配置，无法发送验证邮件"})


@router.get("/auth/verify-email", response_class=HTMLResponse)
async def verify_email_change(request: Request, token: str):
    from app.main import templates
    payload = verify_token(token)
    if not payload or payload.get("scope") != "change_email":
        return templates.TemplateResponse("auth/verify.html", {
            "request": request, "error": "验证链接无效或已过期"
        })
    user_id = int(payload["sub"])
    new_email = payload.get("new_email", "")
    if not new_email:
        return templates.TemplateResponse("auth/verify.html", {
            "request": request, "error": "验证链接无效"
        })
    async with AsyncSessionLocal() as db:
        u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not u:
            return templates.TemplateResponse("auth/verify.html", {
                "request": request, "error": "用户不存在"
            })
        u.email = new_email
        await db.commit()
    return templates.TemplateResponse("auth/verify.html", {
        "request": request,
        "success": '邮箱已修改为 ' + new_email + '！<a href="/profile">返回个人空间</a>'
    })
