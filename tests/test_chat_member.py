from types import SimpleNamespace

from bot import db
from bot.handlers.chat_member import track_chat_owner


def make_event(chat_id, from_user_id, old_status, new_status):
    return SimpleNamespace(
        chat=SimpleNamespace(id=chat_id),
        from_user=SimpleNamespace(id=from_user_id),
        old_chat_member=SimpleNamespace(status=old_status),
        new_chat_member=SimpleNamespace(status=new_status),
    )


async def test_bot_added_as_member_records_inviter(conn):
    event = make_event(chat_id=100, from_user_id=555, old_status="left", new_status="member")

    await track_chat_owner(event, conn)

    assert await db.get_chat_owner(conn, 100) == 555


async def test_bot_added_as_administrator_records_inviter(conn):
    event = make_event(chat_id=100, from_user_id=555, old_status="left", new_status="administrator")

    await track_chat_owner(event, conn)

    assert await db.get_chat_owner(conn, 100) == 555


async def test_bot_promoted_from_member_to_admin_does_not_change_owner(conn):
    await db.set_chat_owner(conn, chat_id=100, inviter_user_id=1)
    event = make_event(chat_id=100, from_user_id=777, old_status="member", new_status="administrator")

    await track_chat_owner(event, conn)

    assert await db.get_chat_owner(conn, 100) == 1


async def test_bot_kicked_does_not_record_owner(conn):
    event = make_event(chat_id=100, from_user_id=555, old_status="member", new_status="kicked")

    await track_chat_owner(event, conn)

    assert await db.get_chat_owner(conn, 100) is None


async def test_bot_re_added_by_different_user_updates_owner(conn):
    first_add = make_event(chat_id=100, from_user_id=1, old_status="left", new_status="member")
    await track_chat_owner(first_add, conn)

    second_add = make_event(chat_id=100, from_user_id=2, old_status="kicked", new_status="member")
    await track_chat_owner(second_add, conn)

    assert await db.get_chat_owner(conn, 100) == 2
