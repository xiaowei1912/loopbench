"""Gymnasium-shaped env around one upstream driver.

The eval runner only calls reset, step, and close. It reads metrics from info.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from loopbench_bridges.images import find_image, find_state
from loopbench_spec.schema import TASKS, EpisodeTrace


def unpack_step(result):
    if not isinstance(result, tuple):
        raise RuntimeError("Upstream env.step did not return a tuple.")
    if len(result) == 5:
        obs, reward, terminated, truncated, info = result
        return obs, float(reward or 0.0), bool(terminated), bool(truncated), info or {}
    if len(result) == 4:
        obs, reward, done, info = result
        return obs, float(reward or 0.0), bool(done), False, info or {}
    raise RuntimeError(f"Upstream env.step returned {len(result)} values.")


class BridgeEnv:
    def __init__(self, driver, *, expose_privileged: bool, render_size: int) -> None:
        self.driver = driver
        self.expose_privileged = expose_privileged
        self.render_size = render_size
        self._last: dict[str, Any] = {}

    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None):
        options = options or {}
        raw = self.driver.reset(
            task=str(options.get("task", "pick_place")),
            factors=dict(options.get("factors") or {}),
            seed=0 if seed is None else int(seed),
            render_size=self.render_size,
        )
        self._last = raw
        return self._obs(raw), self._info(raw)

    def step(self, action):
        raw = self.driver.step(np.asarray(action, dtype=np.float64))
        self._last = raw
        return self._obs(raw), raw["reward"], raw["terminated"], raw["truncated"], self._info(raw)

    def close(self):
        self.driver.close()

    def _obs(self, raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "observation.image": raw["image"],
            "observation.state": np.asarray(raw["state"], dtype=np.float32),
            "task": raw["language"],
        }

    def _info(self, raw: dict[str, Any]) -> dict[str, Any]:
        task = raw["task"]
        needs = TASKS[task].needs_grasp if task in TASKS else True
        trace = EpisodeTrace(
            task=task,
            success=bool(raw["success"]),
            steps=int(raw["steps"]),
            path_length=0.0,
            collisions=0,
            slips=0,
            grasp_attempts=0,
            wrong_grasps=0,
            ever_grasped_target=bool(raw["success"]),
            needs_grasp=needs,
            goal_error=None,
            events=list(raw["events"]),
        )
        info = {
            "task_id": task,
            "language": raw["language"],
            "fixtures": {"upstream_id": raw["upstream_id"]},
            "materials": {},
            "assets": {},
            "camera_model": {"size": self.render_size},
            "control": {"workspace": {"x": [0.0, 1.0], "y": [0.0, 1.0], "z": [0.0, 1.0]}, "block_radius": 0.05},
            "metrics": trace.model_dump(),
            "upstream": {"id": raw["upstream_id"], "factors_applied": False},
        }
        if self.expose_privileged:
            info["privileged"] = {"upstream_id": raw["upstream_id"], "note": "native env state is not mapped into tabletop bodies"}
        return info


def pack_observation(obs, *, task: str, upstream_id: str, language: str, steps: int, reward: float, terminated: bool, truncated: bool, success: bool, events: list[str], render_size: int) -> dict[str, Any]:
    image = find_image(obs, size=render_size)
    state = find_state(obs)
    return {
        "image": image,
        "state": state,
        "task": task,
        "language": language or upstream_id,
        "upstream_id": upstream_id,
        "steps": steps,
        "reward": reward,
        "terminated": terminated,
        "truncated": truncated,
        "success": success,
        "events": events,
    }
