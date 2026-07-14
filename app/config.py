import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

_DB_URL = os.getenv("DATABASE_URL", "")
if _DB_URL:
    DATABASE_URL = _DB_URL
else:
    _mysql_host = os.getenv("MYSQL_HOST", "localhost")
    _mysql_port = os.getenv("MYSQL_PORT", "3306")
    _mysql_db = os.getenv("MYSQL_DATABASE", "gamecluster")
    _mysql_user = os.getenv("MYSQL_USER", "gamecluster")
    _mysql_pass = os.getenv("MYSQL_PASSWORD", "changeme")
    DATABASE_URL = f"mysql+asyncmy://{_mysql_user}:{_mysql_pass}@{_mysql_host}:{_mysql_port}/{_mysql_db}"

_redis_host = os.getenv("REDIS_HOST", "localhost")
_redis_port = os.getenv("REDIS_PORT", "6379")
_redis_pass = os.getenv("REDIS_PASSWORD", "")
if _redis_pass:
    REDIS_URL = f"redis://:{_redis_pass}@{_redis_host}:{_redis_port}/0"
else:
    REDIS_URL = f"redis://{_redis_host}:{_redis_port}/0"
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or SECRET_KEY == "change-me-in-production":
    raise RuntimeError("SECRET_KEY 未设置或使用了默认值，请在生产环境中设置强随机密钥")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

DEFAULT_SITE_TITLE = "小游戏集群"
DEFAULT_SITE_SUBTITLE = "一个有趣的迷你游戏合集"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
GAMES_DIR = os.path.join(os.path.dirname(__file__), "games")
UPLOADS_DIR = os.path.join(STATIC_DIR, "uploads")
