from aiogram import Router

from bot import db

router = Router(name="chat_member_tracker")

_ACTIVE_STATUSES = {"member", "administrator"}
_INACTIVE_STATUSES = {"left", "kicked"}


@router.my_chat_member()
async def track_chat_owner(event, conn) -> None:
    was_inactive = event.old_chat_member.status in _INACTIVE_STATUSES
    is_active = event.new_chat_member.status in _ACTIVE_STATUSES
    if was_inactive and is_active:
        await db.set_chat_owner(conn, event.chat.id, event.from_user.id)
