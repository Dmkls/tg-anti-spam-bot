import importlib

from bot.config import Config


def test_main_module_imports_without_running():
    module = importlib.import_module("bot.__main__")
    assert hasattr(module, "main")


def test_build_bot_without_proxy_uses_plain_session():
    from bot.__main__ import build_bot

    config = Config(bot_token="123456:test-token-abc", proxy_url=None)
    bot = build_bot(config)

    assert bot.session.proxy is None


def test_build_bot_with_proxy_configures_session_proxy():
    from bot.__main__ import build_bot

    config = Config(bot_token="123456:test-token-abc", proxy_url="socks5://user:pass@127.0.0.1:1080")
    bot = build_bot(config)

    assert bot.session.proxy == "socks5://user:pass@127.0.0.1:1080"


def test_build_bot_without_trust_system_certs_does_not_inject_truststore(monkeypatch):
    import bot.__main__ as main_module

    called = []
    monkeypatch.setattr(main_module.truststore, "inject_into_ssl", lambda: called.append(True))

    config = Config(bot_token="123456:test-token-abc", trust_system_certs=False)
    main_module.build_bot(config)

    assert called == []


def test_build_bot_with_trust_system_certs_injects_truststore(monkeypatch):
    import bot.__main__ as main_module

    called = []
    monkeypatch.setattr(main_module.truststore, "inject_into_ssl", lambda: called.append(True))

    config = Config(bot_token="123456:test-token-abc", trust_system_certs=True)
    main_module.build_bot(config)

    assert called == [True]
