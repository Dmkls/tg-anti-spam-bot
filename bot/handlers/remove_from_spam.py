from aiogram import Router
from aiogram.filters import Command, CommandObject

from bot import db
from bot.admin_cache import AdminCache

router = Router(name="remove_from_spam")


@router.message(Command("remove_from_spam"))
async def remove_from_spam_handler(
    message, bot, conn, admin_cache: AdminCache, command: CommandObject
) -> None:
    chat_id = message.chat.id
    sender_id = message.from_user.id

    if not await admin_cache.is_admin(bot, chat_id, sender_id):
        return

    args = (command.args or "").strip()
    if not args.isdigit():
        await message.reply("Использование: /remove_from_spam <id>")
        return

    spam_id = int(args)
    removed = await db.remove_spam_text(conn, chat_id, spam_id)
    if removed:
        await message.reply(f"✅ Запись #{spam_id} удалена.")
    else:
        await message.reply(f"⚠️ Запись #{spam_id} не найдена в этом чате.")
