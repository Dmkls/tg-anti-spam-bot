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


def test_load_config_defaults_proxy_url_to_none(monkeypatch):
    monkeypatch.setattr("bot.config.load_dotenv", lambda: None)
    monkeypatch.setenv("BOT_TOKEN", "test-token-123")
    monkeypatch.delenv("BOT_PROXY_URL", raising=False)
    config = load_config()
    assert config.proxy_url is None


def test_load_config_reads_proxy_url(monkeypatch):
    monkeypatch.setattr("bot.config.load_dotenv", lambda: None)
    monkeypatch.setenv("BOT_TOKEN", "test-token-123")
    monkeypatch.setenv("BOT_PROXY_URL", "socks5://user:pass@127.0.0.1:1080")
    config = load_config()
    assert config.proxy_url == "socks5://user:pass@127.0.0.1:1080"


def test_load_config_treats_empty_proxy_url_as_none(monkeypatch):
    monkeypatch.setattr("bot.config.load_dotenv", lambda: None)
    monkeypatch.setenv("BOT_TOKEN", "test-token-123")
    monkeypatch.setenv("BOT_PROXY_URL", "")
    config = load_config()
    assert config.proxy_url is None
