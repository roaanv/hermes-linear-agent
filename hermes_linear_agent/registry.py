"""Plugin-local registry for the active Linear Agent adapter.

The active adapter is kept in a small process-wide holder registered under its own name in
``sys.modules`` — not in a global of this module. Hermes can force-rediscover plugins in a
running gateway, which evicts and re-executes this package: the connected adapter keeps a
reference to the old module while tool handlers registered by the new load import a fresh
one. A plain module global therefore made every ``linear_agent_*`` tool report "not
currently connected" while the platform was connected. The holder is outside the plugin's
module namespace, so every load of the plugin in the process shares it. Standard library
only — no private Hermes APIs (see tests/test_plugin_contract.py).
"""

from __future__ import annotations

import sys
import types
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .adapter import LinearAgentAdapter

_STATE_MODULE_NAME = "hermes_linear_agent_runtime_state"


def _state() -> types.ModuleType:
    """The process-wide holder, created on first use and shared by every plugin load."""
    state = sys.modules.get(_STATE_MODULE_NAME)
    if state is None:
        fresh = types.ModuleType(_STATE_MODULE_NAME, "Process-wide Linear Agent adapter holder.")
        fresh.active_adapter = None
        state = sys.modules.setdefault(_STATE_MODULE_NAME, fresh)
    return state


def set_active_adapter(adapter: LinearAgentAdapter | None) -> None:
    """Register or clear the currently connected Linear Agent adapter."""
    _state().active_adapter = adapter


def get_active_adapter() -> LinearAgentAdapter:
    """Return the currently connected Linear Agent adapter."""
    adapter = getattr(_state(), "active_adapter", None)
    if adapter is None:
        raise RuntimeError(
            "linear_agent platform is not currently connected. "
            "Make sure the Linear Agent plugin is enabled and the gateway is running."
        )
    return adapter
