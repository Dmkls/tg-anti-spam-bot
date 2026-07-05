from types import SimpleNamespace

from bot import db
from bot.admin_cache import AdminCache
from bot.handlers.remove_from_spam import remove_from_spam_handler
from tests.conftest import make_bot, make_message, make_user


def make_command(args):
    return SimpleNamespace(args=args)


async def test_non_admin_is_ignored(conn):
    spam_id, _ = await db.add_spam_text(conn, chat_id=100, text="spam", added_by=1)
    bot = make_bot(admins=[1])
    admin_cache = AdminCache(clock=lambda: 0.0)
    message = make_message(chat_id=100, user=make_user(2), text=f"/remove_from_spam {spam_id}")

    await remove_from_spam_handler(message, bot, conn, admin_cache, make_command(str(spam_id)))

    message.reply.assert_not_awaited()
    assert await db.find_spam_text(conn, 100, "spam") is not None


async def test_missing_args_shows_usage(conn):
    bot = make_bot(admins=[1])
    admin_cache = AdminCache(clock=lambda: 0.0)
    message = make_message(chat_id=100, user=make_user(1), text="/remove_from_spam")

    await remove_from_spam_handler(message, bot, conn, admin_cache, make_command(None))

    assert "Использование" in message.reply.await_args.args[0]


async def test_non_numeric_args_shows_usage(conn):
    bot = make_bot(admins=[1])
    admin_cache = AdminCache(clock=lambda: 0.0)
    message = make_message(chat_id=100, user=make_user(1), text="/remove_from_spam abc")

    await remove_from_spam_handler(message, bot, conn, admin_cache, make_command("abc"))

    assert "Использование" in message.reply.await_args.args[0]


async def test_removes_existing_entry(conn):
    spam_id, _ = await db.add_spam_text(conn, chat_id=100, text="spam", added_by=1)
    bot = make_bot(admins=[1])
    admin_cache = AdminCache(clock=lambda: 0.0)
    message = make_message(chat_id=100, user=make_user(1), text=f"/remove_from_spam {spam_id}")

    await remove_from_spam_handler(message, bot, conn, admin_cache, make_command(str(spam_id)))

    assert await db.find_spam_text(conn, 100, "spam") is None
    assert "удалена" in message.reply.await_args.args[0]


async def test_unknown_id_reports_not_found(conn):
    bot = make_bot(admins=[1])
    admin_cache = AdminCache(clock=lambda: 0.0)
    message = make_message(chat_id=100, user=make_user(1), text="/remove_from_spam 999")

    await remove_from_spam_handler(message, bot, conn, admin_cache, make_command("999"))

    assert "не найдена" in message.reply.await_args.args[0]
