"""Promote or demote a user.

Role is deliberately not settable through the API, so this is the only way in.

    python scripts/make_admin.py alex@example.com
    python scripts/make_admin.py alex@example.com --demote
"""

import argparse
import asyncio
import sys

sys.path.insert(0, ".")

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.services.auth_service import AuthService  # noqa: E402


async def main(email: str, demote: bool) -> int:
    async with AsyncSessionLocal() as db:
        user = await AuthService.get_by_email(db, email)
        if user is None:
            print(f"No user with email {email!r}")
            return 1
        user.role = "user" if demote else "admin"
        await db.commit()
        print(f"{user.email} is now {user.role!r}")
        return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("email")
    ap.add_argument("--demote", action="store_true")
    a = ap.parse_args()
    raise SystemExit(asyncio.run(main(a.email, a.demote)))
