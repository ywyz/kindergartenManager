import asyncio
from app.auth.password import hash_password
from app.core.database import AsyncSessionLocal
from app.core.models.user import User, UserRole


async def create_test_teacher():
    async with AsyncSessionLocal() as session:
        tenant_id = 1
        username = "teacher"
        password = "teacher123456"
        display_name = "李老师"

        existing = await session.execute(
            User.__table__.select().where(
                User.tenant_id == tenant_id,
                User.username == username,
            )
        )
        if existing.scalar_one_or_none():
            print(f"用户 {username} 已存在")
            return

        user = User(
            tenant_id=tenant_id,
            username=username,
            hashed_password=hash_password(password),
            role=UserRole.teacher,
            is_active=True,
            display_name=display_name,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        print(f"测试教师账号创建成功！")
        print(f"用户名: {username}")
        print(f"密码: {password}")
        print(f"角色: 教师")


if __name__ == "__main__":
    asyncio.run(create_test_teacher())