from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.admin_cache import AdminCache


def make_fake_bot(admin_ids):
    members = [SimpleNamespace(user=SimpleNamespace(id=uid)) for uid in admin_ids]
    return SimpleNamespace(get_chat_administrators=AsyncMock(return_value=members))


async def test_get_admin_ids_returns_ids_from_bot():
    bot = make_fake_bot([1, 2, 3])
    cache = AdminCache()

    admin_ids = await cache.get_admin_ids(bot, chat_id=100)

    assert admin_ids == {1, 2, 3}
    bot.get_chat_administrators.assert_awaited_once_with(100)


async def test_is_admin_true_and_false():
    bot = make_fake_bot([1, 2])
    cache = AdminCache()

    assert await cache.is_admin(bot, chat_id=100, user_id=1) is True
    assert await cache.is_admin(bot, chat_id=100, user_id=999) is False


async def test_second_call_within_ttl_uses_cache():
    bot = make_fake_bot([1])
    clock_values = iter([0.0, 10.0])
    cache = AdminCache(ttl=300, clock=lambda: next(clock_values))

    await cache.get_admin_ids(bot, chat_id=100)
    await cache.get_admin_ids(bot, chat_id=100)

    bot.get_chat_administrators.assert_awaited_once_with(100)


async def test_call_after_ttl_refreshes_cache():
    bot = make_fake_bot([1])
    clock_values = iter([0.0, 301.0])
    cache = AdminCache(ttl=300, clock=lambda: next(clock_values))

    await cache.get_admin_ids(bot, chat_id=100)
    await cache.get_admin_ids(bot, chat_id=100)

    assert bot.get_chat_administrators.await_count == 2


async def test_cache_is_per_chat():
    bot = make_fake_bot([1])
    cache = AdminCache(clock=lambda: 0.0)

    await cache.get_admin_ids(bot, chat_id=100)
    await cache.get_admin_ids(bot, chat_id=200)

    assert bot.get_chat_administrators.await_count == 2
