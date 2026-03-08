# tests/conftest.py
import sys
import types
import pytest
from typing import Any, cast

@pytest.fixture(scope="session", autouse=True)
def setup_streamlit_environment():
    """
    Globally fixes 'ImportError: cannot import name config'.
    Uses ModuleType to satisfy the internal logger without breaking AppTest.
    """
    modules_any = cast(dict[str, Any], sys.modules)

    # 1. Create a real Module object for 'streamlit.config'
    if "streamlit.config" not in modules_any:
        mod_config = types.ModuleType("streamlit.config")
        # Satisfy the logger's specific method call
        mod_config.get_config = lambda *a, **k: None # type: ignore
        modules_any["streamlit.config"] = mod_config

    # 2. Mock other internal paths required for runtime initialization
    paths = [
        "streamlit.runtime",
        "streamlit.runtime.scriptrunner",
        "streamlit.runtime.scriptrunner.script_run_context"
    ]
    for path in paths:
        if path not in modules_any:
            modules_any[path] = types.ModuleType(path)