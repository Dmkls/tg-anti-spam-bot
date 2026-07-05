from bot import db
from bot.admin_cache import AdminCache
from bot.handlers.automod import automod_handler
from tests.conftest import make_bot, make_message, make_user


async def test_non_matching_text_is_left_alone(conn):
    await db.add_spam_text(conn, chat_id=100, text="known spam", added_by=1)
    bot = make_bot(admins=[1])
    admin_cache = AdminCache(clock=lambda: 0.0)
    message = make_message(chat_id=100, user=make_user(50), text="totally unrelated message")

    await automod_handler(message, bot, conn, admin_cache)

    message.delete.assert_not_awaited()
    bot.ban_chat_member.assert_not_awaited()


async def test_exact_match_deletes_and_bans(conn):
    await db.add_spam_text(conn, chat_id=100, text="known spam", added_by=1)
    await db.set_chat_owner(conn, chat_id=100, inviter_user_id=777)
    bot = make_bot(admins=[1])
    admin_cache = AdminCache(clock=lambda: 0.0)
    message = make_message(chat_id=100, user=make_user(50, username="spammer"), text="known spam")

    await automod_handler(message, bot, conn, admin_cache)

    message.delete.assert_awaited_once()
    bot.ban_chat_member.assert_awaited_once_with(100, 50)
    bot.send_message.assert_awaited_once()
    assert bot.send_message.await_args.args[0] == 777


async def test_case_and_whitespace_differences_do_not_match(conn):
    await db.add_spam_text(conn, chat_id=100, text="known spam", added_by=1)
    bot = make_bot(admins=[1])
    admin_cache = AdminCache(clock=lambda: 0.0)
    message = make_message(chat_id=100, user=make_user(50), text="Known Spam")

    await automod_handler(message, bot, conn, admin_cache)

    message.delete.assert_not_awaited()


async def test_admin_sender_is_never_touched(conn):
    await db.add_spam_text(conn, chat_id=100, text="known spam", added_by=1)
    bot = make_bot(admins=[1])
    admin_cache = AdminCache(clock=lambda: 0.0)
    message = make_message(chat_id=100, user=make_user(1), text="known spam")

    await automod_handler(message, bot, conn, admin_cache)

    message.delete.assert_not_awaited()
    bot.ban_chat_member.assert_not_awaited()


async def test_bot_sender_is_never_touched(conn):
    await db.add_spam_text(conn, chat_id=100, text="known spam", added_by=1)
    bot = make_bot(bot_id=999, admins=[1])
    admin_cache = AdminCache(clock=lambda: 0.0)
    message = make_message(chat_id=100, user=make_user(999), text="known spam")

    await automod_handler(message, bot, conn, admin_cache)

    message.delete.assert_not_awaited()
    bot.ban_chat_member.assert_not_awaited()


async def test_missing_chat_owner_skips_dm_without_error(conn):
    await db.add_spam_text(conn, chat_id=100, text="known spam", added_by=1)
    bot = make_bot(admins=[1])
    admin_cache = AdminCache(clock=lambda: 0.0)
    message = make_message(chat_id=100, user=make_user(50), text="known spam")

    await automod_handler(message, bot, conn, admin_cache)

    bot.send_message.assert_not_awaited()


async def test_dm_failure_does_not_raise(conn):
    await db.add_spam_text(conn, chat_id=100, text="known spam", added_by=1)
    await db.set_chat_owner(conn, chat_id=100, inviter_user_id=777)
    bot = make_bot(admins=[1], raise_on_send_message=True)
    admin_cache = AdminCache(clock=lambda: 0.0)
    message = make_message(chat_id=100, user=make_user(50), text="known spam")

    await automod_handler(message, bot, conn, admin_cache)

    message.delete.assert_awaited_once()
    bot.ban_chat_member.assert_awaited_once()
