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
