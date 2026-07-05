# Antispam Telegram Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Telegram bot that lets chat admins mark a message's exact
text as spam (`/add_to_spam`), then auto-deletes any future message with an
identical text and bans its sender, per
`docs/superpowers/specs/2026-07-05-antispam-bot-design.md`.

**Architecture:** Single Python process using aiogram 3.x with long polling.
Business logic lives in small modules (`bot/db.py`, `bot/admin_cache.py`)
that are independent of the Telegram framework where possible, wired
together by thin aiogram `Router` handlers under `bot/handlers/`. Storage is
one SQLite file (`bot.db`) via `aiosqlite`, with all tables keyed by
`chat_id` so one bot instance serves many chats.

**Tech Stack:** Python 3.11+, aiogram 3.x, aiosqlite, python-dotenv, pytest,
pytest-asyncio.

## Global Constraints

- Python 3.11+, aiogram 3.x, long polling only — no webhook, no HTTPS server.
- Storage is a single SQLite file `bot.db` via `aiosqlite`; chats are
  separated by a `chat_id` column, not separate files.
- Config comes from `.env` (`BOT_TOKEN`, optional `BOT_DB_PATH`), loaded via
  `python-dotenv`. `.env` is git-ignored; `.env.example` is committed.
- Text matching is byte-exact: case, whitespace, and newlines all matter.
  Matching compares `message.text` only (plain text, so URLs behind
  `text_link` entities never affect matching).
- Chat admins/owner and the bot itself are always exempt from automod
  (never auto-deleted/banned).
- Bans are permanent (`ban_chat_member` with no `until_date`).
- Admin-status lookups are cached per chat with a TTL of 300 seconds
  (`CACHE_TTL_SECONDS = 300`) to avoid hammering the Telegram API.
- Automod never posts in the group chat. It only sends a silent-failure DM
  to the chat's recorded inviter; a failed DM (user never started the bot)
  is logged and dropped, never retried.
- Direct admin commands (`/add_to_spam`, `/list_spam`, `/remove_from_spam`)
  DO reply in the chat with a short confirmation. Non-admins get silently
  ignored (no "you're not allowed" message).

---

## File Structure

```
bot/
  __init__.py
  __main__.py            # entrypoint: builds Bot/Dispatcher, wires routers, starts polling
  config.py               # .env loading -> Config
  db.py                    # aiosqlite schema + CRUD for spam_texts, chat_owners
  admin_cache.py           # TTL-cached admin-id lookup
  handlers/
    __init__.py
    add_to_spam.py
    list_spam.py
    remove_from_spam.py
    chat_member.py         # tracks who added the bot to a chat
    automod.py             # auto-delete + auto-ban on exact spam match
tests/
  __init__.py
  conftest.py              # shared fakes: make_bot, make_user, make_message, conn fixture
  test_config.py
  test_db.py
  test_admin_cache.py
  test_add_to_spam.py
  test_list_spam.py
  test_remove_from_spam.py
  test_chat_member.py
  test_automod.py
requirements.txt
requirements-dev.txt
pytest.ini
.env.example
.gitignore
README.md
```

---

### Task 1: Project scaffolding + config loading

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `pytest.ini`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `bot/__init__.py`
- Create: `bot/config.py`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`

**Interfaces:**
- Consumes: nothing (first task)
- Produces:
  - `bot/config.py`: `@dataclass class Config: bot_token: str; db_path: str = "bot.db"` and `def load_config() -> Config` (raises `RuntimeError` if `BOT_TOKEN` is unset)

- [ ] **Step 1: Create `requirements.txt`**

```
aiogram>=3.4,<4
aiosqlite>=0.19,<1
python-dotenv>=1.0,<2
```

- [ ] **Step 2: Create `requirements-dev.txt`**

```
-r requirements.txt
pytest>=7.4,<8
pytest-asyncio>=0.23,<1
```

- [ ] **Step 3: Create `pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 4: Create `.gitignore`**

```
__pycache__/
*.pyc
.venv/
venv/
.env
bot.db
```

- [ ] **Step 5: Create `.env.example`**

```
BOT_TOKEN=paste-your-telegram-bot-token-here
BOT_DB_PATH=bot.db
```

- [ ] **Step 6: Create `bot/__init__.py`** (empty file)

- [ ] **Step 7: Create `tests/__init__.py`** (empty file)

- [ ] **Step 8: Write the failing test for config loading**

Create `tests/test_config.py`:

```python
import pytest

from bot.config import load_config


def test_load_config_raises_without_token(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.setattr("bot.config.load_dotenv", lambda: None)
    with pytest.raises(RuntimeError):
        load_config()


def test_load_config_reads_token_and_default_db_path(monkeypatch):
    monkeypatch.setattr("bot.config.load_dotenv", lambda: None)
    monkeypatch.setenv("BOT_TOKEN", "test-token-123")
    monkeypatch.delenv("BOT_DB_PATH", raising=False)
    config = load_config()
    assert config.bot_token == "test-token-123"
    assert config.db_path == "bot.db"


def test_load_config_reads_custom_db_path(monkeypatch):
    monkeypatch.setattr("bot.config.load_dotenv", lambda: None)
    monkeypatch.setenv("BOT_TOKEN", "test-token-123")
    monkeypatch.setenv("BOT_DB_PATH", "custom.db")
    config = load_config()
    assert config.db_path == "custom.db"
```

- [ ] **Step 9: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.config'` (or similar import error)

- [ ] **Step 10: Write minimal implementation**

Create `bot/config.py`:

```python
import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Config:
    bot_token: str
    db_path: str = "bot.db"


def load_config() -> Config:
    load_dotenv()
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "BOT_TOKEN is not set. Copy .env.example to .env and fill it in."
        )
    db_path = os.environ.get("BOT_DB_PATH", "bot.db")
    return Config(bot_token=token, db_path=db_path)
```

- [ ] **Step 11: Install dependencies**

Run: `pip install -r requirements-dev.txt`
Expected: packages install without errors

- [ ] **Step 12: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: 3 passed

- [ ] **Step 13: Commit**

```bash
git add requirements.txt requirements-dev.txt pytest.ini .gitignore .env.example bot/__init__.py bot/config.py tests/__init__.py tests/test_config.py
git commit -m "Add project scaffolding and .env-based config loading"
```

---

### Task 2: Database layer (spam_texts + chat_owners)

**Files:**
- Create: `bot/db.py`
- Test: `tests/test_db.py`

**Interfaces:**
- Consumes: `aiosqlite` (external library)
- Produces (`bot/db.py`):
  - `async def init_db(db_path: str) -> aiosqlite.Connection`
  - `@dataclass class SpamText: id: int; chat_id: int; text: str; added_by: int; added_at: str`
  - `async def add_spam_text(conn, chat_id: int, text: str, added_by: int) -> tuple[int, bool]` — returns `(id, created)`; `created=False` when the `(chat_id, text)` pair already existed
  - `async def find_spam_text(conn, chat_id: int, text: str) -> SpamText | None`
  - `async def list_spam_texts(conn, chat_id: int) -> list[SpamText]` — ordered by `id`
  - `async def remove_spam_text(conn, chat_id: int, spam_id: int) -> bool` — `True` if a row was deleted
  - `async def set_chat_owner(conn, chat_id: int, inviter_user_id: int) -> None` — upsert
  - `async def get_chat_owner(conn, chat_id: int) -> int | None`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_db.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_db.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.db'`

- [ ] **Step 3: Write the implementation**

Create `bot/db.py`:

```python
from dataclasses import dataclass
from datetime import datetime, timezone

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS spam_texts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    added_by INTEGER NOT NULL,
    added_at TEXT NOT NULL,
    UNIQUE(chat_id, text)
);

CREATE TABLE IF NOT EXISTS chat_owners (
    chat_id INTEGER PRIMARY KEY,
    inviter_user_id INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);
"""


@dataclass
class SpamText:
    id: int
    chat_id: int
    text: str
    added_by: int
    added_at: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def init_db(db_path: str) -> aiosqlite.Connection:
    conn = await aiosqlite.connect(db_path)
    await conn.executescript(SCHEMA)
    await conn.commit()
    return conn


async def add_spam_text(
    conn: aiosqlite.Connection, chat_id: int, text: str, added_by: int
) -> tuple[int, bool]:
    cursor = await conn.execute(
        "INSERT OR IGNORE INTO spam_texts (chat_id, text, added_by, added_at) "
        "VALUES (?, ?, ?, ?)",
        (chat_id, text, added_by, _now()),
    )
    await conn.commit()
    if cursor.rowcount == 0:
        existing = await conn.execute(
            "SELECT id FROM spam_texts WHERE chat_id = ? AND text = ?",
            (chat_id, text),
        )
        row = await existing.fetchone()
        return row[0], False
    return cursor.lastrowid, True


async def find_spam_text(
    conn: aiosqlite.Connection, chat_id: int, text: str
) -> SpamText | None:
    cursor = await conn.execute(
        "SELECT id, chat_id, text, added_by, added_at FROM spam_texts "
        "WHERE chat_id = ? AND text = ?",
        (chat_id, text),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return SpamText(*row)


async def list_spam_texts(conn: aiosqlite.Connection, chat_id: int) -> list[SpamText]:
    cursor = await conn.execute(
        "SELECT id, chat_id, text, added_by, added_at FROM spam_texts "
        "WHERE chat_id = ? ORDER BY id",
        (chat_id,),
    )
    rows = await cursor.fetchall()
    return [SpamText(*row) for row in rows]


async def remove_spam_text(conn: aiosqlite.Connection, chat_id: int, spam_id: int) -> bool:
    cursor = await conn.execute(
        "DELETE FROM spam_texts WHERE chat_id = ? AND id = ?", (chat_id, spam_id)
    )
    await conn.commit()
    return cursor.rowcount > 0


async def set_chat_owner(
    conn: aiosqlite.Connection, chat_id: int, inviter_user_id: int
) -> None:
    await conn.execute(
        """
        INSERT INTO chat_owners (chat_id, inviter_user_id, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET
            inviter_user_id = excluded.inviter_user_id,
            updated_at = excluded.updated_at
        """,
        (chat_id, inviter_user_id, _now()),
    )
    await conn.commit()


async def get_chat_owner(conn: aiosqlite.Connection, chat_id: int) -> int | None:
    cursor = await conn.execute(
        "SELECT inviter_user_id FROM chat_owners WHERE chat_id = ?", (chat_id,)
    )
    row = await cursor.fetchone()
    return row[0] if row else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_db.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add bot/db.py tests/test_db.py
git commit -m "Add SQLite-backed data layer for spam texts and chat owners"
```

---

### Task 3: Admin-status cache

**Files:**
- Create: `bot/admin_cache.py`
- Test: `tests/test_admin_cache.py`

**Interfaces:**
- Consumes: `aiogram.Bot` (only calls `bot.get_chat_administrators(chat_id)`, so tests use a fake with that one async method)
- Produces (`bot/admin_cache.py`):
  - `CACHE_TTL_SECONDS: float = 300`
  - `class AdminCache: def __init__(self, ttl: float = CACHE_TTL_SECONDS, clock: Callable[[], float] = time.monotonic)`
  - `async def AdminCache.get_admin_ids(self, bot, chat_id: int) -> set[int]`
  - `async def AdminCache.is_admin(self, bot, chat_id: int, user_id: int) -> bool`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_admin_cache.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_admin_cache.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.admin_cache'`

- [ ] **Step 3: Write the implementation**

Create `bot/admin_cache.py`:

```python
import time
from typing import Callable

CACHE_TTL_SECONDS = 300.0


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
        admin_ids = await self.get_admin_ids(bot, chat_id)
        return user_id in admin_ids
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_admin_cache.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add bot/admin_cache.py tests/test_admin_cache.py
git commit -m "Add TTL-cached admin lookup"
```

---

### Task 4: Shared test fakes + `/add_to_spam` handler

**Files:**
- Create: `tests/conftest.py`
- Create: `bot/handlers/__init__.py`
- Create: `bot/handlers/add_to_spam.py`
- Test: `tests/test_add_to_spam.py`

**Interfaces:**
- Consumes: `bot.db` (Task 2), `bot.admin_cache.AdminCache` (Task 3)
- Produces:
  - `tests/conftest.py`: `make_bot(bot_id=999, admins=None, raise_on_ban=False) -> SimpleNamespace`, `make_user(user_id, username="spammer", full_name="Spam Mer") -> SimpleNamespace`, `make_message(chat_id, user, text, reply_to_message=None, chat_title="Test Chat") -> SimpleNamespace`, `async def conn()` pytest fixture yielding an in-memory `aiosqlite.Connection` with schema applied
  - `bot/handlers/add_to_spam.py`: `router` (aiogram `Router`), `async def add_to_spam_handler(message, bot, conn, admin_cache) -> None`

- [ ] **Step 1: Create shared test fakes**

Create `tests/conftest.py`:

```python
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
```

- [ ] **Step 2: Create `bot/handlers/__init__.py`** (empty file)

- [ ] **Step 3: Write the failing tests**

Create `tests/test_add_to_spam.py`:

```python
from bot import db
from bot.admin_cache import AdminCache
from bot.handlers.add_to_spam import add_to_spam_handler
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
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `python -m pytest tests/test_add_to_spam.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.handlers.add_to_spam'`

- [ ] **Step 5: Write the implementation**

Create `bot/handlers/add_to_spam.py`:

```python
from aiogram import Router
from aiogram.filters import Command

from bot import db
from bot.admin_cache import AdminCache

router = Router(name="add_to_spam")


@router.message(Command("add_to_spam"))
async def add_to_spam_handler(message, bot, conn, admin_cache: AdminCache) -> None:
    chat_id = message.chat.id
    sender_id = message.from_user.id

    if not await admin_cache.is_admin(bot, chat_id, sender_id):
        return

    replied = message.reply_to_message
    if replied is None or not replied.text:
        await message.reply("⚠️ В этом сообщении нет текста для сохранения.")
        return

    spam_id, _created = await db.add_spam_text(
        conn, chat_id=chat_id, text=replied.text, added_by=sender_id
    )

    author = replied.from_user

    if author.id == bot.id:
        await message.reply(f"✅ Добавлено в спам-лист (#{spam_id}).")
        return

    try:
        await replied.delete()
    except Exception:
        await message.reply(
            f"⚠️ Текст сохранён (#{spam_id}), но не удалось удалить/забанить — "
            "проверьте права бота (Delete messages, Ban users)."
        )
        return

    if await admin_cache.is_admin(bot, chat_id, author.id):
        await message.reply(
            f"✅ Добавлено в спам-лист (#{spam_id}). Сообщение удалено "
            "(автор — админ, бан пропущен)."
        )
        return

    try:
        await bot.ban_chat_member(chat_id, author.id)
    except Exception:
        await message.reply(
            f"✅ Добавлено в спам-лист (#{spam_id}). Сообщение удалено, но "
            "забанить автора не удалось — проверьте права бота (Ban users)."
        )
        return

    await message.reply(f"✅ Добавлено в спам-лист (#{spam_id}). Автор забанен.")
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_add_to_spam.py -v`
Expected: 6 passed

- [ ] **Step 7: Commit**

```bash
git add tests/conftest.py bot/handlers/__init__.py bot/handlers/add_to_spam.py tests/test_add_to_spam.py
git commit -m "Add /add_to_spam handler with test fakes"
```

---

### Task 5: `/list_spam` handler

**Files:**
- Create: `bot/handlers/list_spam.py`
- Test: `tests/test_list_spam.py`

**Interfaces:**
- Consumes: `bot.db.list_spam_texts` (Task 2), `bot.admin_cache.AdminCache` (Task 3), `tests/conftest.py` fakes (Task 4)
- Produces: `bot/handlers/list_spam.py`: `router`, `async def list_spam_handler(message, bot, conn, admin_cache) -> None`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_list_spam.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_list_spam.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.handlers.list_spam'`

- [ ] **Step 3: Write the implementation**

Create `bot/handlers/list_spam.py`:

```python
from aiogram import Router
from aiogram.filters import Command

from bot import db
from bot.admin_cache import AdminCache
from bot.db import SpamText

router = Router(name="list_spam")


def _format_entry(entry: SpamText) -> str:
    text = entry.text.replace("\n", " ")
    if len(text) > 80:
        text = text[:77] + "..."
    return f"#{entry.id}: {text}"


@router.message(Command("list_spam"))
async def list_spam_handler(message, bot, conn, admin_cache: AdminCache) -> None:
    chat_id = message.chat.id
    sender_id = message.from_user.id

    if not await admin_cache.is_admin(bot, chat_id, sender_id):
        return

    entries = await db.list_spam_texts(conn, chat_id)
    if not entries:
        await message.reply("Список спама для этого чата пуст.")
        return

    await message.reply("\n".join(_format_entry(entry) for entry in entries))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_list_spam.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add bot/handlers/list_spam.py tests/test_list_spam.py
git commit -m "Add /list_spam handler"
```

---

### Task 6: `/remove_from_spam` handler

**Files:**
- Create: `bot/handlers/remove_from_spam.py`
- Test: `tests/test_remove_from_spam.py`

**Interfaces:**
- Consumes: `bot.db.remove_spam_text` (Task 2), `bot.admin_cache.AdminCache` (Task 3), `aiogram.filters.CommandObject`
- Produces: `bot/handlers/remove_from_spam.py`: `router`, `async def remove_from_spam_handler(message, bot, conn, admin_cache, command) -> None`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_remove_from_spam.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_remove_from_spam.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.handlers.remove_from_spam'`

- [ ] **Step 3: Write the implementation**

Create `bot/handlers/remove_from_spam.py`:

```python
from aiogram import Router
from aiogram.filters import Command, CommandObject

from bot import db
from bot.admin_cache import AdminCache

router = Router(name="remove_from_spam")


@router.message(Command("remove_from_spam"))
async def remove_from_spam_handler(
    message, bot, conn, admin_cache: AdminCache, command: CommandObject
) -> None:
    chat_id = message.chat.id
    sender_id = message.from_user.id

    if not await admin_cache.is_admin(bot, chat_id, sender_id):
        return

    args = (command.args or "").strip()
    if not args.isdigit():
        await message.reply("Использование: /remove_from_spam <id>")
        return

    spam_id = int(args)
    removed = await db.remove_spam_text(conn, chat_id, spam_id)
    if removed:
        await message.reply(f"✅ Запись #{spam_id} удалена.")
    else:
        await message.reply(f"⚠️ Запись #{spam_id} не найдена в этом чате.")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_remove_from_spam.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add bot/handlers/remove_from_spam.py tests/test_remove_from_spam.py
git commit -m "Add /remove_from_spam handler"
```

---

### Task 7: Chat-owner tracking (`my_chat_member`)

**Files:**
- Create: `bot/handlers/chat_member.py`
- Test: `tests/test_chat_member.py`

**Interfaces:**
- Consumes: `bot.db.set_chat_owner` (Task 2), `aiogram.enums.ChatMemberStatus`
- Produces: `bot/handlers/chat_member.py`: `router`, `async def track_chat_owner(event, conn) -> None`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_chat_member.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_chat_member.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.handlers.chat_member'`

- [ ] **Step 3: Write the implementation**

Create `bot/handlers/chat_member.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_chat_member.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add bot/handlers/chat_member.py tests/test_chat_member.py
git commit -m "Track which user added the bot to each chat"
```

---

### Task 8: Automoderation handler

**Files:**
- Create: `bot/handlers/automod.py`
- Test: `tests/test_automod.py`

**Interfaces:**
- Consumes: `bot.db.find_spam_text`, `bot.db.get_chat_owner` (Task 2), `bot.admin_cache.AdminCache` (Task 3), `tests/conftest.py` fakes (Task 4)
- Produces: `bot/handlers/automod.py`: `router`, `async def automod_handler(message, bot, conn, admin_cache) -> None`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_automod.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_automod.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.handlers.automod'`

- [ ] **Step 3: Write the implementation**

Create `bot/handlers/automod.py`:

```python
import logging

from aiogram import F, Router

from bot import db
from bot.admin_cache import AdminCache

router = Router(name="automod")
logger = logging.getLogger(__name__)


@router.message(F.text, ~F.text.startswith("/"))
async def automod_handler(message, bot, conn, admin_cache: AdminCache) -> None:
    chat_id = message.chat.id
    sender = message.from_user

    if sender.id == bot.id:
        return
    if await admin_cache.is_admin(bot, chat_id, sender.id):
        return

    spam_entry = await db.find_spam_text(conn, chat_id, message.text)
    if spam_entry is None:
        return

    try:
        await message.delete()
        await bot.ban_chat_member(chat_id, sender.id)
    except Exception:
        logger.exception(
            "Failed to delete/ban for spam match in chat %s from user %s",
            chat_id,
            sender.id,
        )
        return

    owner_id = await db.get_chat_owner(conn, chat_id)
    if owner_id is None:
        return

    username = f"@{sender.username}" if sender.username else sender.full_name
    try:
        await bot.send_message(
            owner_id,
            f"🛑 В чате «{message.chat.title}» удалено спам-сообщение от "
            f"{username}, автор забанен.",
        )
    except Exception:
        logger.info("Could not DM chat owner %s (likely no /start)", owner_id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_automod.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add bot/handlers/automod.py tests/test_automod.py
git commit -m "Add automoderation: exact-match delete + ban + owner DM"
```

---

### Task 9: Wire the app together, README, manual verification

**Files:**
- Create: `bot/__main__.py`
- Create: `README.md`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: all routers from Tasks 4-8, `bot.config.load_config` (Task 1), `bot.db.init_db` (Task 2), `bot.admin_cache.AdminCache` (Task 3)
- Produces: `bot/__main__.py`: `async def main() -> None` (entrypoint, only runs under `if __name__ == "__main__"`)

- [ ] **Step 1: Write the failing smoke test**

Create `tests/test_main.py`:

```python
import importlib


def test_main_module_imports_without_running():
    module = importlib.import_module("bot.__main__")
    assert hasattr(module, "main")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_main.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.__main__'`

- [ ] **Step 3: Write the implementation**

Create `bot/__main__.py`:

```python
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.admin_cache import AdminCache
from bot.config import load_config
from bot.db import init_db
from bot.handlers.add_to_spam import router as add_to_spam_router
from bot.handlers.automod import router as automod_router
from bot.handlers.chat_member import router as chat_member_router
from bot.handlers.list_spam import router as list_spam_router
from bot.handlers.remove_from_spam import router as remove_from_spam_router


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    config = load_config()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(add_to_spam_router)
    dispatcher.include_router(list_spam_router)
    dispatcher.include_router(remove_from_spam_router)
    dispatcher.include_router(chat_member_router)
    dispatcher.include_router(automod_router)

    conn = await init_db(config.db_path)
    admin_cache = AdminCache()

    try:
        await dispatcher.start_polling(bot, conn=conn, admin_cache=admin_cache)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_main.py -v`
Expected: 1 passed

- [ ] **Step 5: Run the full test suite**

Run: `python -m pytest -v`
Expected: all tests pass (Tasks 1-9 combined)

- [ ] **Step 6: Write `README.md`**

```markdown
# Antispam Telegram Bot

Deletes messages whose text exactly matches a spam text an admin has
flagged, and bans the sender in that chat.

## Setup

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy its
   token.
2. Copy `.env.example` to `.env` and paste the token into `BOT_TOKEN`.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Add the bot to your group as an **administrator** with these two rights
   enabled: **Delete messages** and **Ban users**. Without them, spam
   detection will save entries but cannot delete/ban.
5. Run the bot:
   ```bash
   python -m bot
   ```

## Commands (admins/owner only)

- `/add_to_spam` — reply to a message with this command to save its exact
  text as spam. The message is deleted and its author is banned (unless the
  author is an admin, in which case only the message is deleted).
- `/list_spam` — list saved spam texts for this chat.
- `/remove_from_spam <id>` — remove a saved spam text by its number from
  `/list_spam`.

## How automoderation works

Every non-command text message is compared byte-for-byte (case, spaces, and
line breaks all matter) against this chat's saved spam texts. A match is
deleted and the sender is banned, silently — nothing is posted to the
group. If the person who added the bot to the chat has ever pressed
**Start** in a private chat with the bot, they get a DM about the action;
otherwise it's just logged.

## Manual verification checklist

Automated tests cover the logic; Telegram's real API behavior must be
checked by hand in a test group:

- [ ] Bot joins a test group as admin with Delete messages + Ban users.
- [ ] Non-admin's `/add_to_spam` is ignored.
- [ ] Admin replies `/add_to_spam` to a regular user's message → message
      deleted, user banned, confirmation reply shown.
- [ ] Admin replies `/add_to_spam` to another admin's message → message
      deleted, admin NOT banned.
- [ ] A second, unrelated user sends the exact same spam text → deleted +
      banned automatically, no message posted to the group.
- [ ] The same text with different case/whitespace is NOT auto-deleted.
- [ ] `/list_spam` shows the saved entry; `/remove_from_spam <id>` removes
      it and it no longer triggers automod.
- [ ] The user who added the bot receives a DM after an automod action
      (having pressed Start beforehand).
```

- [ ] **Step 7: Commit**

```bash
git add bot/__main__.py README.md tests/test_main.py
git commit -m "Wire routers into an entrypoint and document setup"
```

---

## Self-Review Notes

- **Spec coverage:** scaffolding/config (Task 1), `spam_texts`/`chat_owners`
  tables (Task 2), admin-cache TTL (Task 3), `/add_to_spam` incl. admin/bot
  exemptions (Task 4), `/list_spam` (Task 5), `/remove_from_spam` (Task 6),
  `my_chat_member` owner tracking (Task 7), automod incl. silent DM and
  exact-match rules (Task 8), wiring + bot-permission README + manual
  checklist (Task 9) — every spec section maps to a task.
- **Type consistency:** `conn` is `aiosqlite.Connection` everywhere;
  `admin_cache` is always `AdminCache`; handler signatures
  `(message, bot, conn, admin_cache[, command])` are consistent across
  Tasks 4-8 and match how `bot/__main__.py` injects them via
  `dispatcher.start_polling(bot, conn=conn, admin_cache=admin_cache)`.
- **No placeholders:** all steps contain full runnable code, including every
  test in `tests/test_chat_member.py` (Task 7).
