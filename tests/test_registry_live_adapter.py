"""The tools must find the connected adapter even after Hermes re-imports the plugin.

Hermes can force-rediscover plugins in a running gateway (``discover_and_load(force=True)``
evicts and re-executes plugin modules). The connected adapter keeps a reference to the OLD
``registry`` module, while tool handlers registered by the new load import a fresh
``registry`` — so every ``linear_agent_*`` tool failed with "platform is not currently
connected" while the platform was connected (observed live on 2026-09-28). The active
adapter must live in process-wide state that survives re-execution of the plugin modules,
and the lookup must still fail closed when nothing is connected.
"""

from __future__ import annotations

import importlib.util
import sys

import pytest

from hermes_linear_agent import registry


def _fresh_registry_copy(name: str):
    """Execute registry.py again as a separate module — what a forced plugin re-import does."""
    spec = importlib.util.spec_from_file_location(name, registry.__file__)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _clean_registry():
    registry.set_active_adapter(None)
    yield
    registry.set_active_adapter(None)
    for name in [n for n in sys.modules if n.startswith("_registry_copy_")]:
        del sys.modules[name]


def test_adapter_registered_in_one_load_is_visible_to_a_reloaded_copy():
    adapter = object()
    registry.set_active_adapter(adapter)
    reloaded = _fresh_registry_copy("_registry_copy_a")
    assert reloaded.get_active_adapter() is adapter


def test_adapter_registered_by_a_reloaded_copy_is_visible_to_the_original():
    adapter = object()
    _fresh_registry_copy("_registry_copy_b").set_active_adapter(adapter)
    assert registry.get_active_adapter() is adapter


def test_disconnect_in_any_copy_clears_for_all():
    registry.set_active_adapter(object())
    _fresh_registry_copy("_registry_copy_c").set_active_adapter(None)
    with pytest.raises(RuntimeError, match="not currently connected"):
        registry.get_active_adapter()


def test_fails_closed_when_nothing_is_connected():
    with pytest.raises(RuntimeError, match="not currently connected"):
        registry.get_active_adapter()
