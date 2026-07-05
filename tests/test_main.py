import importlib
import subprocess
import sys
from pathlib import Path

from bot.config import Config

PROJECT_ROOT = Path(__file__).resolve().parent.parent


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


def _run_subprocess_check(trust_system_certs_value: str, expect_injected: bool) -> None:
    # Run in a fresh subprocess: injecting truststore mutates the global
    # ssl.SSLContext for the whole process, and aiohttp caches its default
    # SSL context at import time, so this can only be observed correctly by
    # controlling import order from a clean interpreter, not in-process.
    script = (
        "import os\n"
        f"os.environ['BOT_TRUST_SYSTEM_CERTS'] = {trust_system_certs_value!r}\n"
        "os.environ.setdefault('BOT_TOKEN', '123456:dummy')\n"
        "import bot.__main__\n"
        "import ssl\n"
        "import truststore\n"
        f"assert (ssl.SSLContext is truststore.SSLContext) is {expect_injected}, ssl.SSLContext\n"
        "print('OK')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_trust_system_certs_env_var_injects_truststore_before_aiohttp_import():
    _run_subprocess_check("true", expect_injected=True)


def test_without_trust_system_certs_env_var_does_not_inject_truststore():
    _run_subprocess_check("false", expect_injected=False)
