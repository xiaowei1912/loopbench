"""Privileged oracle. A ceiling for the benchmark, not a deployable policy."""

from __future__ import annotations

import numpy as np

from loopbench_policies.control import Controller, CtrlBody
from loopbench_spec.schema import TASKS


class OraclePolicy:
    name = "oracle"
    needs_privileged = True

    def __init__(self) -> None:
        self.controller = Controller(clearance=True, careful_transport=False)
        self.phase = "approach"

    def reset(self) -> None:
        self.controller.reset()
        self.phase = "approach"

    def select_action(self, observation: dict, info: dict | None = None) -> np.ndarray:
        del observation
        if not info or "privileged" not in info:
            raise RuntimeError("OraclePolicy requires info['privileged']. The runner only attaches it when needs_privileged is set.")
        privileged = info["privileged"]
        holding = privileged["holding"]
        friction = privileged["factors"].get("friction", "nominal")
        self.controller.careful_transport = friction == "low" and holding is not None
        self.controller.configure(
            workspace=info.get("control", {}).get("workspace"),
            block_radius=info.get("control", {}).get("block_radius"),
        )
        block = float(info.get("control", {}).get("block_radius", 0.058))
        bodies = [_body(raw, block) for raw in privileged["bodies"]]
        goal = _goal(privileged, info["fixtures"])
        ee = np.asarray(privileged["ee"], dtype=np.float64)
        action = self.controller.act(ee, bodies, holding, goal)
        self.phase = self.controller.phase
        return action


def _body(raw: dict, block_radius: float) -> CtrlBody:
    radius = block_radius if raw["role"] == "obstacle" else float(raw["radius"])
    return CtrlBody(
        id=raw["id"],
        x=float(raw["x"]),
        y=float(raw["y"]),
        z=float(raw["z"]),
        sx=float(raw["sx"]),
        sy=float(raw["sy"]),
        sz=float(raw["sz"]),
        color=raw["color"],
        role=raw["role"],
        radius=radius,
    )


def _goal(privileged: dict, fixtures: dict) -> dict:
    task = privileged["task"]
    color = privileged["target_color"]
    if task in {"pick_place", "sort"}:
        bin_pose = fixtures["bin"]
        return {
            "kind": "place",
            "x": bin_pose["x"],
            "y": bin_pose["y"],
            "z": 0.05,
            "tol": bin_pose["half"] * 0.4,
            "target_color": color,
        }
    if task == "stack":
        stack = fixtures["stack"]
        return {
            "kind": "stack",
            "x": 0.0,
            "y": 0.0,
            "z": 0.12,
            "tol": 0.028,
            "target_color": stack["target_color"],
            "support_color": stack["support_color"],
        }
    if task == "push":
        zone = fixtures["zone"]
        return {
            "kind": "push",
            "x": zone["x"],
            "y": zone["y"],
            "z": 0.02,
            "tol": zone["tol"],
            "target_color": "gray",
        }
    if task == "drawer":
        return {
            "kind": "drawer",
            "x": fixtures["drawer_open_x"],
            "y": fixtures["drawer_y"],
            "z": 0.035,
            "tol": 0.02,
            "target_color": "wood",
        }
    raise KeyError(task)


def task_label(task: str) -> str:
    return TASKS[task].label
