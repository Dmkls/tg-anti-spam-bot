import asyncio
import logging

from aiogram import Router
from aiogram.filters import Command

from bot import db
from bot.admin_cache import AdminCache

router = Router(name="add_to_spam")
logger = logging.getLogger(__name__)

CONFIRMATION_DELETE_DELAY_SECONDS = 10


async def _delete_after_delay(bot, chat_id: int, message_id: int, delay: float) -> None:
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        logger.debug("Could not delete message %s in chat %s", message_id, chat_id)


def schedule_deletion(bot, chat_id: int, message_id: int) -> asyncio.Task:
    return asyncio.create_task(
        _delete_after_delay(bot, chat_id, message_id, CONFIRMATION_DELETE_DELAY_SECONDS)
    )


async def _reply_and_schedule_cleanup(bot, message, text: str) -> None:
    confirmation = await message.reply(text)
    schedule_deletion(bot, message.chat.id, message.message_id)
    schedule_deletion(bot, message.chat.id, confirmation.message_id)


@router.message(Command("add_to_spam"))
async def add_to_spam_handler(message, bot, conn, admin_cache: AdminCache) -> None:
    chat_id = message.chat.id
    sender_id = message.from_user.id

    if not await admin_cache.is_admin(bot, chat_id, sender_id):
        return

    replied = message.reply_to_message
    if replied is None or not replied.text:
        await _reply_and_schedule_cleanup(
            bot, message, "⚠️ В этом сообщении нет текста для сохранения."
        )
        return

    spam_id, _created = await db.add_spam_text(
        conn, chat_id=chat_id, text=replied.text, added_by=sender_id
    )

    author = replied.from_user

    if author.id == bot.id:
        await _reply_and_schedule_cleanup(bot, message, f"✅ Добавлено в спам-лист (#{spam_id}).")
        return

    try:
        await replied.delete()
    except Exception:
        await _reply_and_schedule_cleanup(
            bot,
            message,
            f"⚠️ Текст сохранён (#{spam_id}), но не удалось удалить/забанить — "
            "проверьте права бота (Delete messages, Ban users).",
        )
        return

    if await admin_cache.is_admin(bot, chat_id, author.id):
        await _reply_and_schedule_cleanup(
            bot,
            message,
            f"✅ Добавлено в спам-лист (#{spam_id}). Сообщение удалено "
            "(автор — админ, бан пропущен).",
        )
        return

    try:
        await bot.ban_chat_member(chat_id, author.id)
    except Exception:
        await _reply_and_schedule_cleanup(
            bot,
            message,
            f"✅ Добавлено в спам-лист (#{spam_id}). Сообщение удалено, но "
            "забанить автора не удалось — проверьте права бота (Ban users).",
        )
        return

    await _reply_and_schedule_cleanup(
        bot, message, f"✅ Добавлено в спам-лист (#{spam_id}). Автор забанен."
    )
