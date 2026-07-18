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
        mod_config._config_options = {}
        modules_any["streamlit.config"] = mod_config

    # 2. Keep the real Streamlit runtime package intact.
    # Some test runs only need the config module to expose the logger state
    # expected during import, so we patch just that minimal surface here.