"""Plugin discovery.

Repositories do not import each other. They publish entry points and the
product loads whatever is installed. This is the same pattern Gymnasium uses
for environments and the one Isaac Lab uses when it calls `gymnasium.register`.

Groups:

- ``loopbench.simulators`` — object with ``name``, ``probe()``, ``make()``
- ``loopbench.policies`` — object with ``name``, ``make()``, ``improve()``
- ``loopbench.suites`` — a :class:`loopbench_spec.schema.Suite`
"""

from __future__ import annotations

from importlib.metadata import entry_points
from typing import Any

from loopbench_spec.schema import TASKS, Suite, TaskInfo

_CACHE: dict[str, dict[str, Any]] = {}


def clear() -> None:
    _CACHE.clear()


def _group(name: str) -> list[Any]:
    eps = entry_points()
    if hasattr(eps, "select"):
        return list(eps.select(group=name))
    return list(eps.get(name, []))


def _load_group(name: str) -> dict[str, Any]:
    if name in _CACHE:
        return _CACHE[name]
    loaded: dict[str, Any] = {}
    for item in _group(name):
        obj = item.load()
        if isinstance(obj, type):
            obj = obj()
        loaded[item.name] = obj
    _CACHE[name] = loaded
    return loaded


def simulators() -> dict[str, Any]:
    return _load_group("loopbench.simulators")


def policies() -> dict[str, Any]:
    return _load_group("loopbench.policies")


def suites() -> dict[str, Suite]:
    found = _load_group("loopbench.suites")
    for name, suite in found.items():
        if not isinstance(suite, Suite):
            raise TypeError(f"Entry point loopbench.suites:{name} did not return a Suite")
    return found


def simulator(name: str) -> Any:
    found = simulators()
    if name not in found:
        raise KeyError(f"Simulator {name!r} is not installed. Installed: {sorted(found)}")
    return found[name]


def policy(name: str) -> Any:
    found = policies()
    if name not in found:
        raise KeyError(f"Policy {name!r} is not installed. Installed: {sorted(found)}")
    return found[name]


def suite(name: str) -> Suite:
    found = suites()
    if name not in found:
        raise KeyError(f"Suite {name!r} is not installed. Installed: {sorted(found)}")
    return found[name]


def adapters() -> dict[str, Any]:
    return _load_group("loopbench.adapters")


def tasks() -> dict[str, TaskInfo]:
    return dict(TASKS)


def public_info(info: dict[str, Any]) -> dict[str, Any]:
    """Drop privileged state before it reaches a deployable policy."""

    return {key: value for key, value in info.items() if key != "privileged"}
