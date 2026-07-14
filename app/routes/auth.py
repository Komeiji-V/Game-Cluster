from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
import re

from app.services.auth_service import (
    create_user, get_user_by_email, get_user_by_username,
    verify_password, create_access_token, verify_token, verify_user,
)
from app.services.email_service import send_verification_email

router = APIRouter()

EMAIL_RE = re.compile(r"[^@]+@[^@]+\.[^@]+")
MSG_INVALID = "用户名或密码错误"
MSG_BANNED = "账号已被封禁"
MSG_NOT_VERIFIED = "邮箱尚未验证，请检查收件箱"
MSG_PW_MISMATCH = "两次密码不一致"
MSG_USERNAME_LEN = "用户名需 3-32 个字符"
MSG_PW_SHORT = "密码至少 6 位"
MSG_EMAIL_FMT = "邮箱格式不正确"
MSG_USERNAME_TAKEN = "用户名已被占用"
MSG_EMAIL_TAKEN = "邮箱已注册"
MSG_REG_OK = "注册成功！请检查邮箱完成验证。"
MSG_REG_SKIP = "注册成功！（SMTP 未配置，已跳过邮箱验证）"
MSG_VERIFY_FAIL = "验证链接无效或已过期"
MSG_VERIFY_OK = '邮箱验证成功！现在可以<a href="/login">登录</a>了。'
MSG_VERIFY_DUP = "验证失败，可能已经验证过了。"


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    from app.main import templates
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    from app.main import templates
    user = await get_user_by_username(username)
    if not user:
        user = await get_user_by_email(username)
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "auth/login.html", {"request": request, "error": MSG_INVALID}
        )
    if user.is_banned:
        return templates.TemplateResponse(
            "auth/login.html", {"request": request, "error": MSG_BANNED}
        )
    if not user.is_verified:
        return templates.TemplateResponse(
            "auth/login.html", {"request": request, "error": MSG_NOT_VERIFIED}
        )
    token = create_access_token({"sub": str(user.id), "scope": "access"})
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie(key="token", value=token, httponly=True, secure=True, samesite="lax", max_age=60*60*24*7)
    return resp


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    from app.main import templates
    return templates.TemplateResponse("auth/register.html", {"request": request})


@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
):
    from app.main import templates

    if password != password_confirm:
        return templates.TemplateResponse("auth/register.html", {
            "request": request, "error": MSG_PW_MISMATCH
        })
    if len(username) < 3 or len(username) > 32:
        return templates.TemplateResponse("auth/register.html", {
            "request": request, "error": MSG_USERNAME_LEN
        })
    if len(password) < 6:
        return templates.TemplateResponse("auth/register.html", {
            "request": request, "error": MSG_PW_SHORT
        })
    if not EMAIL_RE.match(email):
        return templates.TemplateResponse("auth/register.html", {
            "request": request, "error": MSG_EMAIL_FMT
        })
    if await get_user_by_username(username):
        return templates.TemplateResponse("auth/register.html", {
            "request": request, "error": MSG_USERNAME_TAKEN
        })
    if await get_user_by_email(email):
        return templates.TemplateResponse("auth/register.html", {
            "request": request, "error": MSG_EMAIL_TAKEN
        })

    user = await create_user(username, email, password)
    verify_token_str = create_access_token({"sub": str(user.id), "scope": "verify"})
    base_url = str(request.base_url).rstrip("/")
    verify_url = f"{base_url}/auth/verify?token={verify_token_str}"
    sent = await send_verification_email(email, username, verify_url)

    if sent:
        msg = MSG_REG_OK
    else:
        await verify_user(user.id)
        msg = MSG_REG_SKIP

    return templates.TemplateResponse("auth/register.html", {
        "request": request,
        "success": msg
    })


@router.get("/auth/verify", response_class=HTMLResponse)
async def verify_email(request: Request, token: str):
    from app.main import templates
    payload = verify_token(token)
    if not payload or payload.get("scope") != "verify":
        return templates.TemplateResponse("auth/verify.html", {
            "request": request, "error": MSG_VERIFY_FAIL
        })
    user_id = int(payload["sub"])
    if await verify_user(user_id):
        return templates.TemplateResponse("auth/verify.html", {
            "request": request,
            "success": MSG_VERIFY_OK
        })
    return templates.TemplateResponse("auth/verify.html", {
        "request": request, "error": MSG_VERIFY_DUP
    })


@router.get("/logout")
async def logout():
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie("token", secure=True, samesite="lax")
    return resp
