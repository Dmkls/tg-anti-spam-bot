import asyncio
from unittest.mock import AsyncMock

import bot.handlers.add_to_spam as add_to_spam_module
from bot import db
from bot.admin_cache import AdminCache
from bot.handlers.add_to_spam import CONFIRMATION_DELETE_DELAY_SECONDS, add_to_spam_handler
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


async def test_delete_after_delay_waits_then_deletes_message(monkeypatch):
    sleep_calls = []

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr(add_to_spam_module.asyncio, "sleep", fake_sleep)
    bot = make_bot()

    await add_to_spam_module._delete_after_delay(bot, chat_id=100, message_id=5, delay=10)

    assert sleep_calls == [10]
    bot.delete_message.assert_awaited_once_with(100, 5)


async def test_delete_after_delay_swallows_delete_errors(monkeypatch):
    async def fake_sleep(seconds):
        return None

    monkeypatch.setattr(add_to_spam_module.asyncio, "sleep", fake_sleep)
    bot = make_bot()
    bot.delete_message = AsyncMock(side_effect=RuntimeError("already deleted"))

    await add_to_spam_module._delete_after_delay(bot, chat_id=100, message_id=5, delay=10)


async def test_schedule_deletion_creates_background_task_with_configured_delay():
    calls = []

    async def fake_delete_after_delay(bot, chat_id, message_id, delay):
        calls.append((chat_id, message_id, delay))

    original = add_to_spam_module._delete_after_delay
    add_to_spam_module._delete_after_delay = fake_delete_after_delay
    try:
        bot = make_bot()
        task = add_to_spam_module.schedule_deletion(bot, chat_id=100, message_id=7)
        assert isinstance(task, asyncio.Task)
        await task
    finally:
        add_to_spam_module._delete_after_delay = original

    assert calls == [(100, 7, CONFIRMATION_DELETE_DELAY_SECONDS)]


async def test_success_schedules_deletion_of_command_and_confirmation_messages(conn, monkeypatch):
    scheduled = []
    monkeypatch.setattr(
        add_to_spam_module,
        "schedule_deletion",
        lambda bot, chat_id, message_id: scheduled.append((chat_id, message_id)),
    )

    bot = make_bot(admins=[1])
    admin_cache = AdminCache(clock=lambda: 0.0)
    spammer = make_user(50)
    spam_message = make_message(chat_id=100, user=spammer, text="spam text")
    command_message = make_message(
        chat_id=100, user=make_user(1), text="/add_to_spam", reply_to_message=spam_message
    )
    confirmation_message = make_message(chat_id=100, user=make_user(1), text="confirmation", message_id=999)
    command_message.reply = AsyncMock(return_value=confirmation_message)

    await add_to_spam_handler(command_message, bot, conn, admin_cache)

    assert (100, command_message.message_id) in scheduled
    assert (100, 999) in scheduled
    assert len(scheduled) == 2


async def test_no_text_warning_also_schedules_deletion_of_both_messages(conn, monkeypatch):
    scheduled = []
    monkeypatch.setattr(
        add_to_spam_module,
        "schedule_deletion",
        lambda bot, chat_id, message_id: scheduled.append((chat_id, message_id)),
    )

    bot = make_bot(admins=[1])
    admin_cache = AdminCache(clock=lambda: 0.0)
    sticker_message = make_message(chat_id=100, user=make_user(50), text=None)
    command_message = make_message(
        chat_id=100, user=make_user(1), text="/add_to_spam", reply_to_message=sticker_message
    )
    confirmation_message = make_message(chat_id=100, user=make_user(1), text="warning", message_id=999)
    command_message.reply = AsyncMock(return_value=confirmation_message)

    await add_to_spam_handler(command_message, bot, conn, admin_cache)

    assert (100, command_message.message_id) in scheduled
    assert (100, 999) in scheduled
    assert len(scheduled) == 2
