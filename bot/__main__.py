import asyncio
import logging

import truststore
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from bot.admin_cache import AdminCache
from bot.config import Config, load_config
from bot.db import init_db
from bot.handlers.add_to_spam import router as add_to_spam_router
from bot.handlers.automod import router as automod_router
from bot.handlers.chat_member import router as chat_member_router
from bot.handlers.list_spam import router as list_spam_router
from bot.handlers.remove_from_spam import router as remove_from_spam_router


def build_bot(config: Config) -> Bot:
    if config.trust_system_certs:
        truststore.inject_into_ssl()
    if config.proxy_url:
        return Bot(token=config.bot_token, session=AiohttpSession(proxy=config.proxy_url))
    return Bot(token=config.bot_token)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    config = load_config()

    bot = build_bot(config)
    dispatcher = Dispatcher()
    dispatcher.include_router(add_to_spam_router)
    dispatcher.include_router(list_spam_router)
    dispatcher.include_router(remove_from_spam_router)
    dispatcher.include_router(chat_member_router)
    dispatcher.include_router(automod_router)

    conn = await init_db(config.db_path)
    admin_cache = AdminCache()

    try:
        await dispatcher.start_polling(bot, conn=conn, admin_cache=admin_cache)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
