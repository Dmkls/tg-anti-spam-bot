from aiogram import Router
from aiogram.filters import Command

from bot import db
from bot.admin_cache import AdminCache
from bot.db import SpamText

router = Router(name="list_spam")


def _format_entry(entry: SpamText) -> str:
    text = entry.text.replace("\n", " ")
    if len(text) > 80:
        text = text[:77] + "..."
    return f"#{entry.id}: {text}"


@router.message(Command("list_spam"))
async def list_spam_handler(message, bot, conn, admin_cache: AdminCache) -> None:
    chat_id = message.chat.id
    sender_id = message.from_user.id

    if not await admin_cache.is_admin(bot, chat_id, sender_id):
        return

    entries = await db.list_spam_texts(conn, chat_id)
    if not entries:
        await message.reply("Список спама для этого чата пуст.")
        return

    await message.reply("\n".join(_format_entry(entry) for entry in entries))
