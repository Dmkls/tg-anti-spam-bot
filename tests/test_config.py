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
