"""Collect lit colors with a privileged calibration pass, then freeze them into the policy.

The pass is the lab equivalent of a ColorChecker plus a known camera. After it
returns, evaluation withholds privileged state again.
"""

from __future__ import annotations

import numpy as np

from loopbench_policies.vision import VisionConfig, VisionPolicy
from loopbench_spec.projection import world_to_px
from loopbench_spec.schema import TASKS

CALIBRATION_TASKS = tuple(TASKS)


def improve_vision(policy: VisionPolicy, report: dict, make_env) -> tuple[VisionPolicy, dict]:
    samples = _collect(make_env)
    bank = _bank(policy, samples)
    config = VisionConfig(
        name="vision_v2",
        online_calibration=True,
        clearance=True,
        careful_transport=True,
        threshold=policy.config.threshold,
        prototypes=bank,
    )
    notes = [
        f"颜色原型更新为 {_variant_count(bank)} 个光照变体",
        "打开地标手眼标定",
        "打开柱子避障",
        "搬运步长降到接触跟得上的范围",
    ]
    levers = [item.get("lever") for item in report.get("recommendations", [])]
    return VisionPolicy(config), {
        "policy": config.to_dict(),
        "notes": notes,
        "levers": levers,
        "calibration_scenes": len(samples),
    }


def _collect(make_env) -> list[dict]:
    env = make_env(expose_privileged=True)
    samples = []
    try:
        for lighting in ("nominal", "dim", "glare"):
            for task in CALIBRATION_TASKS:
                obs, info = env.reset(seed=1, options={"task": task, "factors": {"lighting": lighting}})
                privileged = info["privileged"]
                points = [
                    {"color": body["color"], "x": body["x"], "y": body["y"]}
                    for body in privileged["bodies"]
                    if body["color"] in info["materials"]
                ]
                for x, y in info["fixtures"]["fiducials"]:
                    points.append({"color": "magenta", "x": x, "y": y})
                samples.append(
                    {
                        "image": obs["observation.image"],
                        "camera": privileged["camera_offset"],
                        "lighting": lighting,
                        "points": points,
                        "model": info["camera_model"],
                        "materials": info["materials"],
                    }
                )
    finally:
        env.close()
    return samples


def _bank(policy: VisionPolicy, samples: list[dict]) -> dict[str, list[list[int]]]:
    buckets: dict[tuple[str, str], list[tuple[int, int, int]]] = {}
    for sample in samples:
        model = sample["model"]
        cam_dx, cam_dy = sample["camera"]
        for point in sample["points"]:
            u, v = world_to_px(
                point["x"],
                point["y"],
                cam_dx,
                cam_dy,
                size=int(model["size"]),
                world_x=float(model["world_x"]),
                world_y=float(model["world_y"]),
            )
            ui, vi = int(round(u)), int(round(v))
            image = sample["image"]
            if not (0 <= vi < image.shape[0] and 0 <= ui < image.shape[1]):
                continue
            pixel = tuple(int(channel) for channel in image[vi, ui])
            buckets.setdefault((point["color"], sample["lighting"]), []).append(pixel)
    bank: dict[str, list[list[int]]] = {}
    if policy.config.prototypes:
        bank = {key: [list(item) for item in value] for key, value in policy.config.prototypes.items()}
    elif samples and samples[0].get("materials"):
        bank = {key: [list(value)] for key, value in samples[0]["materials"].items()}
    for (color, _lighting), pixels in buckets.items():
        mean = np.mean(np.asarray(pixels, dtype=np.float64), axis=0)
        variant = [int(round(channel)) for channel in mean]
        existing = bank.setdefault(color, [])
        if not any(float(np.linalg.norm(np.array(variant) - np.array(item))) < 12 for item in existing):
            existing.append(variant)
    return bank


def _variant_count(bank: dict) -> int:
    return sum(len(value) for value in bank.values())
