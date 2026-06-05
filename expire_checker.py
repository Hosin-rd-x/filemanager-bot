import asyncio
from datetime import datetime

from database.db import get_all_active_files, deactivate_file
from utils.helpers import is_expired


async def expire_checker(bot):
    """Background loop that deactivates expired or maxed-out files every 60 seconds."""
    while True:
        try:
            files = await get_all_active_files()
            for f in files:
                should_deactivate = False

                # Check expiry
                if f["expire_seconds"] > 0 and is_expired(f["expires_at"]):
                    should_deactivate = True

                # Check download limit
                if f["max_downloads"] > 0 and f["download_count"] >= f["max_downloads"]:
                    should_deactivate = True

                if should_deactivate:
                    await deactivate_file(f["id"])

        except Exception as e:
            print(f"[expire_checker] error: {e}")

        await asyncio.sleep(30)
