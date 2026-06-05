import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from database.db import init_db, add_admin
from handlers import admin, upload, user, blocked
from utils.expire_checker import expire_checker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────
BOT_TOKEN  = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
OWNER_ID   = int(os.getenv("OWNER_ID", "0"))   # Your Telegram user ID


async def main():
    # Init database
    await init_db()

    # Auto-add owner as admin
    if OWNER_ID:
        await add_admin(OWNER_ID)
        logger.info(f"Owner {OWNER_ID} added as admin")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Register routers (order matters — admin must come before user for /start)
    dp.include_router(admin.router)
    dp.include_router(upload.router)
    dp.include_router(blocked.router)
    dp.include_router(user.router)

    # Start background tasks
    asyncio.create_task(expire_checker(bot))

    logger.info("Bot starting...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
