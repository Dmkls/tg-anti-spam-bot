import importlib


def test_main_module_imports_without_running():
    module = importlib.import_module("bot.__main__")
    assert hasattr(module, "main")
