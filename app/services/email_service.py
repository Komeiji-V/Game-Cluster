import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from sqlalchemy import select
from app.config import AsyncSessionLocal
from app.models.site_settings import SiteSettings


async def _get_smtp_config() -> dict:
    async with AsyncSessionLocal() as db:
        keys = ["smtp_host", "smtp_port", "smtp_username", "smtp_password",
                "smtp_from_email", "smtp_from_name", "smtp_use_tls"]
        result = await db.execute(
            select(SiteSettings).where(SiteSettings.setting_key.in_(keys))
        )
        config = {row.setting_key: row.value for row in result.scalars().all()}
        return {
            "host": config.get("smtp_host", ""),
            "port": int(config.get("smtp_port", "587")),
            "username": config.get("smtp_username", ""),
            "password": config.get("smtp_password", ""),
            "from_email": config.get("smtp_from_email", "noreply@gamecluster.local"),
            "from_name": config.get("smtp_from_name", "小游戏集群"),
            "use_tls": config.get("smtp_use_tls", "true").lower() == "true",
        }


def _send_sync(msg: MIMEMultipart, config: dict) -> bool:
    try:
        if config["port"] == 465:
            server = smtplib.SMTP_SSL(config["host"], config["port"], timeout=30)
        else:
            server = smtplib.SMTP(config["host"], config["port"], timeout=30)
            if config["use_tls"]:
                server.ehlo()
                server.starttls()
                server.ehlo()

        if config["username"] and config["password"]:
            server.login(config["username"], config["password"])

        server.send_message(msg, from_addr=config["from_email"], to_addrs=msg["To"])
        server.quit()
        return True
    except Exception:
        return False


async def send_verification_email(to_email: str, username: str, verify_url: str) -> bool:
    config = await _get_smtp_config()
    if not config["host"]:
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = formataddr((config["from_name"], config["from_email"]))
    msg["To"] = to_email
    msg["Subject"] = "验证你的邮箱 - 小游戏集群"

    html = f"""<html><body>
    <h2>{username}，欢迎加入小游戏集群！</h2>
    <p>请点击下方链接验证你的邮箱：</p>
    <p><a href="{verify_url}">验证邮箱</a></p>
    <p>或复制此链接到浏览器：<br>{verify_url}</p>
    </body></html>"""
    msg.attach(MIMEText(html, "html"))

    return await asyncio.to_thread(_send_sync, msg, config)


async def send_email_change_verification(to_email: str, username: str, verify_url: str) -> bool:
    config = await _get_smtp_config()
    if not config["host"]:
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = formataddr((config["from_name"], config["from_email"]))
    msg["To"] = to_email
    msg["Subject"] = "验证邮箱修改 - 小游戏集群"

    html = f"""<html><body>
    <h2>{username}，你正在修改绑定邮箱</h2>
    <p>请点击下方链接确认将邮箱修改为 {to_email}：</p>
    <p><a href="{verify_url}">确认修改</a></p>
    <p>或复制此链接：<br>{verify_url}</p>
    </body></html>"""
    msg.attach(MIMEText(html, "html"))

    return await asyncio.to_thread(_send_sync, msg, config)
