"""Evaluate a policy on a suite.

This module imports the spec and nothing else. The simulator and the policy
are objects the caller loaded from entry points.
"""

from __future__ import annotations

import base64
import io
from collections.abc import Callable

import numpy as np
from PIL import Image

from loopbench_evalkit.analysis import classify
from loopbench_evalkit.suites import iter_episodes
from loopbench_spec.registry import public_info
from loopbench_spec.schema import TASKS, EpisodeTrace, Factors, Suite

Progress = Callable[[int, int, str], None]


def evaluate(
    simulator,
    policy,
    suite: Suite,
    *,
    episodes_per_cell: int = 1,
    seed: int = 0,
    capture_frames: bool = False,
    on_progress: Progress | None = None,
) -> dict:
    env = simulator.make(expose_privileged=bool(getattr(policy, "needs_privileged", False)))
    specs = iter_episodes(suite, episodes_per_cell, seed)
    episodes = []
    total = len(specs)
    try:
        for index, spec in enumerate(specs):
            if on_progress:
                on_progress(index, total, f"{spec.task} · {spec.factors.label()}")
            episodes.append(
                _run(env, policy, spec, index=index, capture_frames=capture_frames)
            )
    finally:
        env.close()
    if on_progress:
        on_progress(total, total, "done")
    return {
        "suite": suite.name,
        "policy": getattr(policy, "name", "policy"),
        "simulator": getattr(simulator, "name", "simulator"),
        "seed": seed,
        "episodes_per_cell": episodes_per_cell,
        "privileged": bool(getattr(policy, "needs_privileged", False)),
        "summary": summarize(episodes),
        "episodes": episodes,
    }


def _run(env, policy, spec, *, index: int, capture_frames: bool) -> dict:
    obs, info = env.reset(
        seed=spec.seed,
        options={"task": spec.task, "factors": spec.factors.model_dump()},
    )
    policy.reset()
    frames: list[tuple[int, np.ndarray]] = []
    if capture_frames:
        frames.append((0, np.array(obs["observation.image"])))
    reward = 0.0
    terminated = False
    truncated = False
    step = 0
    for step in range(1, 10_000):
        viewed = info if getattr(policy, "needs_privileged", False) else public_info(info)
        action = policy.select_action(obs, viewed)
        obs, reward, terminated, truncated, info = env.step(action)
        if capture_frames and step % 12 == 0:
            frames.append((step, np.array(obs["observation.image"])))
        if terminated or truncated:
            break
    if capture_frames:
        frames.append((step, np.array(obs["observation.image"])))
    trace = EpisodeTrace.model_validate(info["metrics"])
    failure = classify(trace)
    label = TASKS[spec.task].label if spec.task in TASKS else spec.task
    return {
        "id": f"ep-{index:03d}",
        "index": index,
        "task": spec.task,
        "task_label": label,
        "seed": spec.seed,
        "factors": spec.factors.model_dump(),
        "factor_label": spec.factors.label(),
        "language": obs["task"],
        "success": bool(trace.success),
        "failure": failure,
        "tags": _tags(failure, spec.factors),
        "phase": getattr(policy, "phase", None),
        "metrics": {
            "steps": trace.steps,
            "path_length": round(trace.path_length, 4),
            "collisions": trace.collisions,
            "slips": trace.slips,
            "grasp_attempts": trace.grasp_attempts,
            "wrong_grasps": trace.wrong_grasps,
            "goal_error": None if trace.goal_error is None else round(float(trace.goal_error), 4),
            "reward": reward,
        },
        "keyframes": [_frame(s, image) for s, image in _thin(frames)] if capture_frames else [],
    }


def _tags(failure: str | None, factors: Factors) -> list[str]:
    if failure is None:
        return []
    changed = factors.differs_from_nominal()
    tags = []
    if failure in {"grasp_miss", "wrong_object", "placement_error"} and (
        "lighting" in changed or "camera" in changed
    ):
        tags.append("perception")
    if failure == "collision" and "clutter" in changed:
        tags.append("geometry")
    if failure == "slip" and changed.get("friction") == "low":
        tags.append("contact")
    return tags


def _thin(frames: list[tuple[int, np.ndarray]]) -> list[tuple[int, np.ndarray]]:
    if len(frames) <= 4:
        return frames
    indexes = {0, len(frames) // 3, (2 * len(frames)) // 3, len(frames) - 1}
    return [frames[index] for index in sorted(indexes)]


def _frame(step: int, image: np.ndarray) -> dict:
    buffer = io.BytesIO()
    Image.fromarray(image, mode="RGB").save(buffer, format="PNG", optimize=True)
    return {"step": step, "png": base64.b64encode(buffer.getvalue()).decode("ascii")}


def summarize(episodes: list[dict]) -> dict:
    if not episodes:
        return {"n": 0, "success": 0, "success_rate": 0.0, "by_task": {}, "by_failure": {}}
    success = sum(1 for episode in episodes if episode["success"])
    by_task: dict[str, dict] = {}
    by_failure: dict[str, int] = {}
    for episode in episodes:
        bucket = by_task.setdefault(episode["task"], {"n": 0, "success": 0, "label": episode["task_label"]})
        bucket["n"] += 1
        bucket["success"] += int(episode["success"])
        if episode["failure"]:
            by_failure[episode["failure"]] = by_failure.get(episode["failure"], 0) + 1
    for bucket in by_task.values():
        bucket["success_rate"] = bucket["success"] / bucket["n"]
    return {
        "n": len(episodes),
        "success": success,
        "success_rate": success / len(episodes),
        "by_task": by_task,
        "by_failure": by_failure,
    }
