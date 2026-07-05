import os
from dataclasses import dataclass

from dotenv import load_dotenv


_TRUE_VALUES = {"1", "true", "yes"}


@dataclass
class Config:
    bot_token: str
    db_path: str = "bot.db"
    proxy_url: str | None = None
    trust_system_certs: bool = False


def load_config() -> Config:
    load_dotenv()
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "BOT_TOKEN is not set. Copy .env.example to .env and fill it in."
        )
    db_path = os.environ.get("BOT_DB_PATH", "bot.db")
    proxy_url = os.environ.get("BOT_PROXY_URL") or None
    trust_system_certs = os.environ.get("BOT_TRUST_SYSTEM_CERTS", "").strip().lower() in _TRUE_VALUES
    return Config(
        bot_token=token,
        db_path=db_path,
        proxy_url=proxy_url,
        trust_system_certs=trust_system_certs,
    )
