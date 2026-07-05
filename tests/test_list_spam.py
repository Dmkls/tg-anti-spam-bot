from bot import db
from bot.admin_cache import AdminCache
from bot.handlers.list_spam import list_spam_handler
from tests.conftest import make_bot, make_message, make_user


async def test_non_admin_is_ignored(conn):
    bot = make_bot(admins=[1])
    admin_cache = AdminCache(clock=lambda: 0.0)
    message = make_message(chat_id=100, user=make_user(2), text="/list_spam")

    await list_spam_handler(message, bot, conn, admin_cache)

    message.reply.assert_not_awaited()


async def test_empty_list_reports_empty(conn):
    bot = make_bot(admins=[1])
    admin_cache = AdminCache(clock=lambda: 0.0)
    message = make_message(chat_id=100, user=make_user(1), text="/list_spam")

    await list_spam_handler(message, bot, conn, admin_cache)

    message.reply.assert_awaited_once()
    assert "пуст" in message.reply.await_args.args[0]


async def test_lists_entries_for_this_chat_only(conn):
    await db.add_spam_text(conn, chat_id=100, text="first spam", added_by=1)
    await db.add_spam_text(conn, chat_id=100, text="second spam", added_by=1)
    await db.add_spam_text(conn, chat_id=200, text="other chat spam", added_by=1)

    bot = make_bot(admins=[1])
    admin_cache = AdminCache(clock=lambda: 0.0)
    message = make_message(chat_id=100, user=make_user(1), text="/list_spam")

    await list_spam_handler(message, bot, conn, admin_cache)

    reply_text = message.reply.await_args.args[0]
    assert "first spam" in reply_text
    assert "second spam" in reply_text
    assert "other chat spam" not in reply_text


async def test_long_text_is_truncated_to_80_chars_and_flattened():
    from bot.handlers.list_spam import _format_entry
    from bot.db import SpamText

    long_text = "x" * 100 + "\nsecond line"
    entry = SpamText(id=1, chat_id=100, text=long_text, added_by=1, added_at="now")

    formatted = _format_entry(entry)

    assert formatted.startswith("#1: ")
    assert "\n" not in formatted
    assert len(formatted) <= len("#1: ") + 80
