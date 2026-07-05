import time
from typing import Callable

CACHE_TTL_SECONDS = 300.0

# Telegram's fixed pseudo-user id for messages sent anonymously "as the
# group" (username @GroupAnonymousBot). This id is the same in every
# Telegram group and never appears in getChatAdministrators, even though
# only an admin/owner can enable anonymous posting in the first place.
GROUP_ANONYMOUS_ADMIN_ID = 1087968824


class AdminCache:
    def __init__(
        self,
        ttl: float = CACHE_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = ttl
        self._clock = clock
        self._cache: dict[int, tuple[float, set[int]]] = {}

    async def get_admin_ids(self, bot, chat_id: int) -> set[int]:
        now = self._clock()
        cached = self._cache.get(chat_id)
        if cached is not None:
            cached_at, admin_ids = cached
            if now - cached_at < self._ttl:
                return admin_ids

        admins = await bot.get_chat_administrators(chat_id)
        admin_ids = {member.user.id for member in admins}
        self._cache[chat_id] = (now, admin_ids)
        return admin_ids

    async def is_admin(self, bot, chat_id: int, user_id: int) -> bool:
        if user_id == GROUP_ANONYMOUS_ADMIN_ID:
            return True
        admin_ids = await self.get_admin_ids(bot, chat_id)
        return user_id in admin_ids
