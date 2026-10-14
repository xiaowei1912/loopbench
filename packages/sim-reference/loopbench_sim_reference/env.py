"""Gymnasium environment. The runner only sees reset, step, and info."""

from __future__ import annotations

from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from loopbench_sim_reference.constants import (
    ASSETS,
    BIN_HALF,
    BIN_XY,
    BLOCK_RADIUS,
    DRAWER_OPEN_X,
    DRAWER_Y,
    FIDUCIALS,
    NOMINAL_RGB,
    RENDER_SIZE,
    WORKSPACE,
    WORLD_X,
    WORLD_Y,
    ZONE_TOL,
    ZONE_XY,
)
from loopbench_sim_reference.world import ReferenceSim
from loopbench_spec.schema import Factors

COLOR_KIND = {
    "red": "cube",
    "green": "cube",
    "blue": "cube",
    "yellow": "cube",
    "gray": "puck",
    "wood": "drawer",
    "obstacle": "obstacle",
}


class TabletopEnv(gym.Env):
    """Quasi-static tabletop registered as ``Loopbench/Tabletop-v0``.

    ``options`` on reset selects the task and the factor cell. Privileged
    state is omitted unless the backend was constructed with
    ``expose_privileged=True`` — that flag is how the oracle and the
    calibration pass are separated from deployable policies.
    """

    metadata = {"render_modes": ["rgb_array"]}

    def __init__(
        self,
        *,
        expose_privileged: bool = False,
        render_size: int = RENDER_SIZE,
        task: str = "pick_place",
        factors: Factors | dict | None = None,
    ) -> None:
        super().__init__()
        self.expose_privileged = expose_privileged
        self.sim = ReferenceSim(render_size=render_size)
        self._task = task
        self._factors = factors if isinstance(factors, Factors) else Factors.model_validate(factors or {})
        size = render_size
        self.observation_space = spaces.Dict(
            {
                "observation.image": spaces.Box(0, 255, shape=(size, size, 3), dtype=np.uint8),
                "observation.state": spaces.Box(-np.inf, np.inf, shape=(4,), dtype=np.float32),
                "task": spaces.Text(max_length=240),
            }
        )
        self.action_space = spaces.Box(
            low=np.array([-0.05, -0.05, -0.05, -1.0], dtype=np.float32),
            high=np.array([0.05, 0.05, 0.05, 1.0], dtype=np.float32),
            dtype=np.float32,
        )

    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None):
        super().reset(seed=seed)
        options = options or {}
        task = str(options.get("task", self._task))
        raw_factors = options.get("factors", self._factors)
        factors = raw_factors if isinstance(raw_factors, Factors) else Factors.model_validate(raw_factors)
        self._task = task
        self._factors = factors
        obs = self.sim.reset(task, factors, 0 if seed is None else int(seed))
        return obs, self._info()

    def step(self, action):
        obs, reward, terminated, truncated, _local = self.sim.step(np.asarray(action, dtype=np.float64))
        return obs, float(reward), bool(terminated), bool(truncated), self._info()

    def render(self):
        return self.sim.observe()["observation.image"]

    def _info(self) -> dict[str, Any]:
        info: dict[str, Any] = {
            "task_id": self.sim.task,
            "language": self.sim.language,
            "fixtures": _fixtures(),
            "materials": {name: list(rgb) for name, rgb in NOMINAL_RGB.items()},
            "assets": {
                color: {"kind": kind, **ASSETS[kind]}
                for color, kind in COLOR_KIND.items()
            },
            "camera_model": {"size": self.sim.render_size, "world_x": WORLD_X, "world_y": WORLD_Y},
            "control": {
                "workspace": {axis: list(bounds) for axis, bounds in WORKSPACE.items()},
                "block_radius": BLOCK_RADIUS,
            },
            "metrics": self.sim.trace().model_dump(),
        }
        if self.expose_privileged:
            info["privileged"] = self.sim.privileged()
        return info


def _fixtures() -> dict[str, Any]:
    return {
        "bin": {"x": BIN_XY[0], "y": BIN_XY[1], "half": BIN_HALF[0]},
        "zone": {"x": ZONE_XY[0], "y": ZONE_XY[1], "tol": ZONE_TOL},
        "drawer_open_x": DRAWER_OPEN_X,
        "drawer_y": DRAWER_Y,
        "fiducials": [list(point) for point in FIDUCIALS],
        "stack": {"target_color": "green", "support_color": "yellow"},
    }


def register_gym() -> str:
    env_id = "Loopbench/Tabletop-v0"
    if env_id not in gym.registry:
        gym.register(id=env_id, entry_point="loopbench_sim_reference.env:TabletopEnv")
    return env_id
