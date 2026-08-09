import asyncio
from app.core.database import AsyncSessionLocal
from app.modules.auth.models import User
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User))
        users = res.scalars().all()
        print(f"Found {len(users)} users")
        for u in users:
            u.role = "admin"
            print(f"Updated user {u.email} to admin")
        await db.commit()

if __name__ == "__main__":
    asyncio.run(main())
