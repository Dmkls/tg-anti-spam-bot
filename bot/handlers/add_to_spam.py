from aiogram import Router
from aiogram.filters import Command

from bot import db
from bot.admin_cache import AdminCache

router = Router(name="add_to_spam")


@router.message(Command("add_to_spam"))
async def add_to_spam_handler(message, bot, conn, admin_cache: AdminCache) -> None:
    chat_id = message.chat.id
    sender_id = message.from_user.id

    if not await admin_cache.is_admin(bot, chat_id, sender_id):
        return

    replied = message.reply_to_message
    if replied is None or not replied.text:
        await message.reply("⚠️ В этом сообщении нет текста для сохранения.")
        return

    spam_id, _created = await db.add_spam_text(
        conn, chat_id=chat_id, text=replied.text, added_by=sender_id
    )

    author = replied.from_user

    if author.id == bot.id:
        await message.reply(f"✅ Добавлено в спам-лист (#{spam_id}).")
        return

    try:
        await replied.delete()
    except Exception:
        await message.reply(
            f"⚠️ Текст сохранён (#{spam_id}), но не удалось удалить/забанить — "
            "проверьте права бота (Delete messages, Ban users)."
        )
        return

    if await admin_cache.is_admin(bot, chat_id, author.id):
        await message.reply(
            f"✅ Добавлено в спам-лист (#{spam_id}). Сообщение удалено "
            "(автор — админ, бан пропущен)."
        )
        return

    try:
        await bot.ban_chat_member(chat_id, author.id)
    except Exception:
        await message.reply(
            f"✅ Добавлено в спам-лист (#{spam_id}). Сообщение удалено, но "
            "забанить автора не удалось — проверьте права бота (Ban users)."
        )
        return

    await message.reply(f"✅ Добавлено в спам-лист (#{spam_id}). Автор забанен.")
