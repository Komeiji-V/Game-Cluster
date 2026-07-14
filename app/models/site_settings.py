from sqlalchemy import Column, String, Boolean, DateTime, Text, func, Integer
from app.models import Base


class SiteSettings(Base):
    __tablename__ = "site_settings"

    setting_key = Column(String(64), primary_key=True)
    value = Column(Text, nullable=True)

    SMTP_KEYS = {
        "smtp_host", "smtp_port", "smtp_username", "smtp_password",
        "smtp_from_email", "smtp_from_name", "smtp_use_tls"
    }
    SITE_KEYS = {
        "site_title", "site_subtitle", "site_favicon", "site_wallpaper",
        "site_primary_color", "site_bg_color", "site_base_url"
    }


class GameModule(Base):
    __tablename__ = "game_modules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(64), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String(16), nullable=False, default="1.0")
    author = Column(String(64), nullable=False, default="unknown")
    enabled = Column(Boolean, default=True)
    installed_at = Column(DateTime(timezone=True), server_default=func.now())
