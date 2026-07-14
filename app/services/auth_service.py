from __future__ import annotations
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, AsyncSessionLocal
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_verify_token(user_id: int) -> str:
    return create_access_token({"sub": str(user_id), "scope": "verify"})


def verify_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_user_by_id(user_id: int) -> User | None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


async def get_user_by_email(email: str) -> User | None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()


async def get_user_by_username(username: str) -> User | None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()


async def create_user(username: str, email: str, password: str) -> User:
    async with AsyncSessionLocal() as db:
        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


async def verify_user(user_id: int) -> bool:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user and not user.is_verified:
            user.is_verified = True
            await db.commit()
            return True
        return False
