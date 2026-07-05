import pytest

from bot import db


@pytest.fixture
async def conn():
    connection = await db.init_db(":memory:")
    yield connection
    await connection.close()


async def test_add_and_find_spam_text_exact_match(conn):
    spam_id, created = await db.add_spam_text(conn, chat_id=1, text="Buy crypto now!!!", added_by=42)
    assert created is True
    assert spam_id > 0

    found = await db.find_spam_text(conn, chat_id=1, text="Buy crypto now!!!")
    assert found is not None
    assert found.id == spam_id
    assert found.chat_id == 1
    assert found.text == "Buy crypto now!!!"
    assert found.added_by == 42


async def test_find_spam_text_is_case_and_whitespace_sensitive(conn):
    await db.add_spam_text(conn, chat_id=1, text="Buy crypto now", added_by=42)

    assert await db.find_spam_text(conn, chat_id=1, text="buy crypto now") is None
    assert await db.find_spam_text(conn, chat_id=1, text="Buy crypto now ") is None
    assert await db.find_spam_text(conn, chat_id=1, text="Buy  crypto now") is None
    assert await db.find_spam_text(conn, chat_id=1, text="Buy crypto now\n") is None


async def test_find_spam_text_is_scoped_to_chat(conn):
    await db.add_spam_text(conn, chat_id=1, text="Buy crypto now", added_by=42)
    assert await db.find_spam_text(conn, chat_id=2, text="Buy crypto now") is None


async def test_add_spam_text_does_not_duplicate(conn):
    first_id, first_created = await db.add_spam_text(conn, chat_id=1, text="dup", added_by=1)
    second_id, second_created = await db.add_spam_text(conn, chat_id=1, text="dup", added_by=2)
    assert first_created is True
    assert second_created is False
    assert first_id == second_id


async def test_list_spam_texts_orders_by_id(conn):
    await db.add_spam_text(conn, chat_id=1, text="first", added_by=1)
    await db.add_spam_text(conn, chat_id=1, text="second", added_by=1)
    await db.add_spam_text(conn, chat_id=2, text="other chat", added_by=1)

    entries = await db.list_spam_texts(conn, chat_id=1)
    assert [e.text for e in entries] == ["first", "second"]


async def test_remove_spam_text(conn):
    spam_id, _ = await db.add_spam_text(conn, chat_id=1, text="remove me", added_by=1)

    assert await db.remove_spam_text(conn, chat_id=1, spam_id=spam_id) is True
    assert await db.find_spam_text(conn, chat_id=1, text="remove me") is None
    assert await db.remove_spam_text(conn, chat_id=1, spam_id=spam_id) is False


async def test_remove_spam_text_is_scoped_to_chat(conn):
    spam_id, _ = await db.add_spam_text(conn, chat_id=1, text="chat one text", added_by=1)
    assert await db.remove_spam_text(conn, chat_id=2, spam_id=spam_id) is False


async def test_set_and_get_chat_owner(conn):
    assert await db.get_chat_owner(conn, chat_id=100) is None

    await db.set_chat_owner(conn, chat_id=100, inviter_user_id=555)
    assert await db.get_chat_owner(conn, chat_id=100) == 555

    await db.set_chat_owner(conn, chat_id=100, inviter_user_id=777)
    assert await db.get_chat_owner(conn, chat_id=100) == 777
