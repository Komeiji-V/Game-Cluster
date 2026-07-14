import asyncio, sys, getpass
sys.path.insert(0, '.')
from app.config import AsyncSessionLocal
from app.models.user import User
from app.services.auth_service import hash_password
from sqlalchemy import select

async def main():
    print("=== 创建/提权管理员 ===")
    name = input("管理员用户名 (默认 admin): ").strip() or "admin"
    email = input("管理员邮箱 (默认 admin@example.com): ").strip() or "admin@example.com"
    pwd = getpass.getpass("管理员密码: ")
    if not pwd or len(pwd) < 6:
        print("密码至少 6 位，已取消")
        return

    async with AsyncSessionLocal() as db:
        r = await db.execute(select(User).where(User.username == name))
        u = r.scalar_one_or_none()
        if u:
            u.is_admin = True
            u.is_verified = True
            u.password_hash = hash_password(pwd)
            print(f'用户 "{name}" 已提权为管理员，密码已更新')
        else:
            u = User(username=name, email=email,
                     password_hash=hash_password(pwd),
                     is_admin=True, is_verified=True)
            db.add(u)
            print(f'管理员 "{name}" 已创建')
        await db.commit()

asyncio.run(main())
