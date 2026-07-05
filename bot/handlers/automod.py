import logging

from aiogram import F, Router

from bot import db
from bot.admin_cache import AdminCache

router = Router(name="automod")
logger = logging.getLogger(__name__)


@router.message(F.text, ~F.text.startswith("/"))
async def automod_handler(message, bot, conn, admin_cache: AdminCache) -> None:
    chat_id = message.chat.id
    sender = message.from_user

    if sender.id == bot.id:
        return
    if await admin_cache.is_admin(bot, chat_id, sender.id):
        return

    spam_entry = await db.find_spam_text(conn, chat_id, message.text)
    if spam_entry is None:
        return

    try:
        await message.delete()
        await bot.ban_chat_member(chat_id, sender.id)
    except Exception:
        logger.exception(
            "Failed to delete/ban for spam match in chat %s from user %s",
            chat_id,
            sender.id,
        )
        return

    owner_id = await db.get_chat_owner(conn, chat_id)
    if owner_id is None:
        return

    username = f"@{sender.username}" if sender.username else sender.full_name
    try:
        await bot.send_message(
            owner_id,
            f"🛑 В чате «{message.chat.title}» удалено спам-сообщение от "
            f"{username}, автор забанен.",
        )
    except Exception:
        logger.info("Could not DM chat owner %s (likely no /start)", owner_id)
