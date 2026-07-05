from bot import db
from bot.admin_cache import AdminCache
from bot.handlers.add_to_spam import add_to_spam_handler
from tests.conftest import make_bot, make_message, make_user


async def test_non_admin_is_ignored(conn):
    bot = make_bot(admins=[1])
    admin_cache = AdminCache(clock=lambda: 0.0)
    spammer = make_user(50)
    spam_message = make_message(chat_id=100, user=spammer, text="spam text")
    command_message = make_message(chat_id=100, user=make_user(2), text="/add_to_spam", reply_to_message=spam_message)

    await add_to_spam_handler(command_message, bot, conn, admin_cache)

    command_message.reply.assert_not_awaited()
    assert await db.find_spam_text(conn, 100, "spam text") is None


async def test_reply_without_text_warns_and_saves_nothing(conn):
    bot = make_bot(admins=[1])
    admin_cache = AdminCache(clock=lambda: 0.0)
    sticker_message = make_message(chat_id=100, user=make_user(50), text=None)
    command_message = make_message(chat_id=100, user=make_user(1), text="/add_to_spam", reply_to_message=sticker_message)

    await add_to_spam_handler(command_message, bot, conn, admin_cache)

    command_message.reply.assert_awaited_once()
    assert "нет текста" in command_message.reply.await_args.args[0]


async def test_regular_author_is_deleted_and_banned(conn):
    bot = make_bot(admins=[1])
    admin_cache = AdminCache(clock=lambda: 0.0)
    spammer = make_user(50)
    spam_message = make_message(chat_id=100, user=spammer, text="spam text")
    command_message = make_message(chat_id=100, user=make_user(1), text="/add_to_spam", reply_to_message=spam_message)

    await add_to_spam_handler(command_message, bot, conn, admin_cache)

    assert await db.find_spam_text(conn, 100, "spam text") is not None
    spam_message.delete.assert_awaited_once()
    bot.ban_chat_member.assert_awaited_once_with(100, 50)
    assert "Автор забанен" in command_message.reply.await_args.args[0]


async def test_admin_author_is_deleted_but_not_banned(conn):
    bot = make_bot(admins=[1, 50])
    admin_cache = AdminCache(clock=lambda: 0.0)
    admin_author = make_user(50)
    spam_message = make_message(chat_id=100, user=admin_author, text="spam text")
    command_message = make_message(chat_id=100, user=make_user(1), text="/add_to_spam", reply_to_message=spam_message)

    await add_to_spam_handler(command_message, bot, conn, admin_cache)

    assert await db.find_spam_text(conn, 100, "spam text") is not None
    spam_message.delete.assert_awaited_once()
    bot.ban_chat_member.assert_not_awaited()
    assert "бан пропущен" in command_message.reply.await_args.args[0]


async def test_bot_author_is_neither_deleted_nor_banned(conn):
    bot = make_bot(bot_id=999, admins=[1])
    admin_cache = AdminCache(clock=lambda: 0.0)
    bot_author = make_user(999)
    spam_message = make_message(chat_id=100, user=bot_author, text="spam text")
    command_message = make_message(chat_id=100, user=make_user(1), text="/add_to_spam", reply_to_message=spam_message)

    await add_to_spam_handler(command_message, bot, conn, admin_cache)

    assert await db.find_spam_text(conn, 100, "spam text") is not None
    spam_message.delete.assert_not_awaited()
    bot.ban_chat_member.assert_not_awaited()


async def test_ban_failure_reports_missing_permissions(conn):
    bot = make_bot(admins=[1], raise_on_ban=True)
    admin_cache = AdminCache(clock=lambda: 0.0)
    spammer = make_user(50)
    spam_message = make_message(chat_id=100, user=spammer, text="spam text")
    command_message = make_message(chat_id=100, user=make_user(1), text="/add_to_spam", reply_to_message=spam_message)

    await add_to_spam_handler(command_message, bot, conn, admin_cache)

    spam_message.delete.assert_awaited_once()
    assert "проверьте права бота" in command_message.reply.await_args.args[0]
