from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot import db


@pytest.fixture
async def conn():
    connection = await db.init_db(":memory:")
    yield connection
    await connection.close()


def make_bot(bot_id=999, admins=None, raise_on_ban=False, raise_on_send_message=False):
    admins = admins or []
    members = [SimpleNamespace(user=SimpleNamespace(id=uid)) for uid in admins]
    bot = SimpleNamespace()
    bot.id = bot_id
    bot.get_chat_administrators = AsyncMock(return_value=members)
    if raise_on_ban:
        bot.ban_chat_member = AsyncMock(side_effect=RuntimeError("no rights"))
    else:
        bot.ban_chat_member = AsyncMock(return_value=True)
    if raise_on_send_message:
        bot.send_message = AsyncMock(side_effect=RuntimeError("forbidden"))
    else:
        bot.send_message = AsyncMock(return_value=None)
    return bot


def make_user(user_id, username="spammer", full_name="Spam Mer"):
    return SimpleNamespace(id=user_id, username=username, full_name=full_name)


def make_message(chat_id, user, text, reply_to_message=None, chat_title="Test Chat"):
    message = SimpleNamespace()
    message.chat = SimpleNamespace(id=chat_id, title=chat_title)
    message.from_user = user
    message.text = text
    message.reply_to_message = reply_to_message
    message.reply = AsyncMock(return_value=None)
    message.delete = AsyncMock(return_value=None)
    return message
