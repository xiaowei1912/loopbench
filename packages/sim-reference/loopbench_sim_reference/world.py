"""Quasi-static tabletop. Same scene factors the benchmark sweeps.

This is a reference backend, not a physics engine. Contact is explicit:
pinch to grasp, slip under fast motion when friction is low, pillars block
the end-effector, and a puck translates when the gripper pushes it.
Seeds fully determine the scene.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from loopbench_sim_reference.constants import (
    ASSETS,
    BIN_HALF,
    BIN_XY,
    DRAWER_CLOSED_X,
    DRAWER_OPEN_X,
    EE_RADIUS,
    EE_START,
    GRASP_XY,
    GRASP_Z,
    HORIZON,
    LAYOUT,
    PILLAR_RADIUS,
    SLIP_LIMIT,
    SLIP_STEP,
    SORT_COLORS,
    WORKSPACE,
    ZONE_TOL,
    ZONE_XY,
)
from loopbench_sim_reference.constants import camera_offset_of
from loopbench_sim_reference.render import render_scene
from loopbench_spec.schema import TASKS, EpisodeTrace, Factors


@dataclass
class Body:
    id: str
    kind: str
    x: float
    y: float
    z: float
    sx: float
    sy: float
    sz: float
    color: str
    movable: bool
    graspable: bool
    role: str
    radius: float
    home_y: float = 0.0
    home_z: float = 0.0


class ReferenceSim:
    name = "reference"

    def __init__(self, render_size: int = 160) -> None:
        self.render_size = render_size
        self.bodies: list[Body] = []
        self.ee_x, self.ee_y, self.ee_z = EE_START
        self.gripper_closed = False
        self.holding: str | None = None
        self.factors = Factors()
        self.task = "pick_place"
        self.step_i = 0
        self.rng = np.random.default_rng(0)
        self.language = ""
        self.target_id = ""
        self.target_color = ""
        self.sort_color = "red"
        self.collisions = 0
        self.slips = 0
        self.grasp_attempts = 0
        self.wrong_grasps = 0
        self.ever_grasped_target = False
        self.slip_accum = 0.0
        self.path_length = 0.0
        self.events: list[str] = []
        self._success_flag = False

    def reset(self, task: str, factors: Factors, seed: int) -> dict:
        if task not in LAYOUT:
            raise KeyError(f"Unknown task {task!r}. Known: {sorted(LAYOUT)}")
        self.task = task
        self.factors = factors
        self.rng = np.random.default_rng(seed)
        self.ee_x, self.ee_y, self.ee_z = EE_START
        self.gripper_closed = False
        self.holding = None
        self.step_i = 0
        self.collisions = 0
        self.slips = 0
        self.grasp_attempts = 0
        self.wrong_grasps = 0
        self.ever_grasped_target = False
        self.slip_accum = 0.0
        self.path_length = 0.0
        self.events = []
        self._success_flag = False
        self.sort_color = SORT_COLORS[int(seed) % len(SORT_COLORS)]
        self.bodies = self._spawn()
        target = next(body for body in self.bodies if body.role == "target")
        self.target_id = target.id
        self.target_color = target.color
        self.language = self._language()
        return self.observe()

    def observe(self) -> dict:
        image = render_scene(
            self.bodies,
            (self.ee_x, self.ee_y, self.ee_z, 1.0 if self.gripper_closed else 0.0),
            self.factors,
            self.render_size,
        )
        proprio = np.array(
            [self.ee_x, self.ee_y, self.ee_z, 1.0 if self.gripper_closed else 0.0],
            dtype=np.float32,
        )
        return {
            "observation.image": image,
            "observation.state": proprio,
            "task": self.language,
        }

    def step(self, action: np.ndarray) -> tuple[dict, float, bool, bool, dict]:
        action = np.asarray(action, dtype=np.float64).reshape(4)
        dx, dy, dz = (float(v) for v in action[:3])
        close = bool(action[3] > 0)
        oldx, oldy = self.ee_x, self.ee_y
        self._move(dx, dy, dz)
        self.path_length += float(np.hypot(self.ee_x - oldx, self.ee_y - oldy))
        step_len = float(np.hypot(self.ee_x - oldx, self.ee_y - oldy))

        was_closed = self.gripper_closed
        was_holding = self.holding
        self.gripper_closed = close
        if self.holding and not close:
            self._release()
        elif self.holding and close:
            self._follow(step_len, was_holding)
        elif not self.holding and close and not was_closed:
            self.grasp_attempts += 1
            self._try_grasp()
        elif not self.holding and not close:
            self._push(self.ee_x - oldx, self.ee_y - oldy)

        self.step_i += 1
        self._success_flag = self._check_success()
        terminated = self._success_flag
        truncated = self.step_i >= HORIZON and not terminated
        info = {
            "success": self._success_flag,
            "holding": self.holding,
            "collisions": self.collisions,
            "slips": self.slips,
        }
        reward = 1.0 if terminated else 0.0
        return self.observe(), reward, terminated, truncated, info

    def privileged(self) -> dict:
        return {
            "ee": (self.ee_x, self.ee_y, self.ee_z, 1.0 if self.gripper_closed else 0.0),
            "holding": self.holding,
            "bodies": [self._body_dict(body) for body in self.bodies],
            "factors": self.factors.model_dump(),
            "camera_offset": list(camera_offset_of(self.factors)),
            "task": self.task,
            "target_id": self.target_id,
            "target_color": self.target_color,
            "language": self.language,
        }

    def trace(self) -> EpisodeTrace:
        return EpisodeTrace(
            task=self.task,
            success=self._success_flag,
            steps=self.step_i,
            path_length=self.path_length,
            collisions=self.collisions,
            slips=self.slips,
            grasp_attempts=self.grasp_attempts,
            wrong_grasps=self.wrong_grasps,
            ever_grasped_target=self.ever_grasped_target,
            needs_grasp=TASKS[self.task].needs_grasp,
            goal_error=self._goal_error(),
            events=list(self.events[-12:]),
        )

    def _spawn(self) -> list[Body]:
        sigma = 0.005 if self.factors.jitter == "low" else 0.018
        bodies: list[Body] = []
        for index, (kind, color, role, x, y) in enumerate(LAYOUT[self.task]):
            asset = ASSETS[kind]
            jx, jy = self.rng.normal(0, sigma, size=2)
            jx = float(np.clip(jx, -0.03, 0.03))
            jy = float(np.clip(jy, -0.03, 0.03))
            if kind == "drawer":
                jx, jy = jx * 0.25, jy * 0.25
            body = Body(
                id=f"{color}-{index}",
                kind=kind,
                x=x + jx,
                y=y + jy,
                z=asset["sz"],
                sx=asset["sx"],
                sy=asset["sy"],
                sz=asset["sz"],
                color=color,
                movable=True,
                graspable=True,
                role=role,
                radius=asset["radius"],
                home_y=y + jy,
                home_z=asset["sz"],
            )
            bodies.append(body)
        if self.task == "sort":
            for body in bodies:
                body.role = "target" if body.color == self.sort_color else "distractor"
        if self.factors.clutter:
            target = next(body for body in bodies if body.role == "target")
            count = 2 if self.factors.clutter >= 2 else 1
            fractions = (0.42, 0.68)[:count]
            for index, fraction in enumerate(fractions):
                px = EE_START[0] + (target.x - EE_START[0]) * fraction
                py = EE_START[1] + (target.y - EE_START[1]) * fraction
                asset = ASSETS["obstacle"]
                bodies.append(
                    Body(
                        id=f"pillar-{index}",
                        kind="obstacle",
                        x=float(px),
                        y=float(py),
                        z=asset["sz"] * 0.5,
                        sx=PILLAR_RADIUS,
                        sy=PILLAR_RADIUS,
                        sz=asset["sz"],
                        color="obstacle",
                        movable=False,
                        graspable=False,
                        role="obstacle",
                        radius=PILLAR_RADIUS,
                    )
                )
        return bodies

    def _language(self) -> str:
        meta = TASKS[self.task]
        instruction = meta.instruction
        if self.task == "sort":
            instruction = instruction.format(color=self.sort_color)
        return instruction

    def _move(self, dx: float, dy: float, dz: float) -> None:
        dx = float(np.clip(dx, -0.05, 0.05))
        dy = float(np.clip(dy, -0.05, 0.05))
        dz = float(np.clip(dz, -0.05, 0.05))
        nx = float(np.clip(self.ee_x + dx, *WORKSPACE["x"]))
        ny = float(np.clip(self.ee_y + dy, *WORKSPACE["y"]))
        nz = float(np.clip(self.ee_z + dz, *WORKSPACE["z"]))
        if self._hits_pillar(nx, ny):
            self.collisions += 1
            self.events.append("collision")
            self.ee_z = nz
            return
        self.ee_x, self.ee_y, self.ee_z = nx, ny, nz

    def _hits_pillar(self, x: float, y: float) -> bool:
        for body in self.bodies:
            if body.role != "obstacle":
                continue
            if np.hypot(x - body.x, y - body.y) < body.radius + EE_RADIUS:
                return True
        return False

    def _try_grasp(self) -> None:
        thresh = GRASP_XY[self.factors.friction]
        best: tuple[float, Body] | None = None
        for body in self.bodies:
            if not body.graspable:
                continue
            dist = float(np.hypot(body.x - self.ee_x, body.y - self.ee_y))
            if dist <= thresh and abs(body.z - self.ee_z) <= GRASP_Z:
                if best is None or dist < best[0]:
                    best = (dist, body)
        if best is None:
            self.events.append("grasp_fail")
            return
        body = best[1]
        self.holding = body.id
        self.slip_accum = 0.0
        body.x, body.y, body.z = self.ee_x, self.ee_y, self.ee_z
        self.events.append(f"grasp:{body.id}")
        if body.id == self.target_id:
            self.ever_grasped_target = True
        else:
            self.wrong_grasps += 1

    def _follow(self, step_len: float, was_holding: bool) -> None:
        body = self._by_id(self.holding)
        if body is None:
            self.holding = None
            return
        if body.kind == "drawer":
            dx = self.ee_x - body.x
            body.x = float(np.clip(body.x + dx, DRAWER_CLOSED_X, DRAWER_OPEN_X + 0.01))
            body.y = body.home_y
            body.z = body.home_z
            self.ee_x, self.ee_y, self.ee_z = body.x, body.y, body.z
        else:
            body.x, body.y, body.z = self.ee_x, self.ee_y, self.ee_z
        if was_holding and self.factors.friction == "low" and body.kind != "obstacle":
            if step_len > SLIP_STEP:
                self.slip_accum += step_len - SLIP_STEP
            if self.slip_accum > SLIP_LIMIT:
                self._slip(body)

    def _slip(self, body: Body) -> None:
        self.events.append("slip")
        self.slips += 1
        self.holding = None
        self.slip_accum = 0.0
        if body.kind != "drawer":
            body.z = body.sz
            body.x = float(np.clip(body.x - 0.08, 0.12, 0.88))

    def _release(self) -> None:
        body = self._by_id(self.holding)
        self.holding = None
        if body is None:
            return
        self.events.append(f"release:{body.id}")
        if body.kind == "drawer":
            body.y = body.home_y
            body.z = body.home_z
            return
        body.x, body.y = self.ee_x, self.ee_y
        body.z = self._rest_z(body)

    def _rest_z(self, body: Body) -> float:
        z = body.sz
        for other in self.bodies:
            if other.id == body.id or other.role == "obstacle":
                continue
            if abs(other.x - body.x) < (other.sx + body.sx) * 0.7 and abs(other.y - body.y) < (
                other.sy + body.sy
            ) * 0.7:
                z = max(z, other.z + other.sz + body.sz)
        return z

    def _push(self, dx: float, dy: float) -> None:
        if abs(dx) + abs(dy) < 1e-6:
            return
        gain = {"low": 1.0, "nominal": 1.0, "high": 0.85}[self.factors.friction]
        for body in self.bodies:
            if body.kind != "puck":
                continue
            if abs(body.z - self.ee_z) > 0.03:
                continue
            reach = body.radius + EE_RADIUS
            if float(np.hypot(body.x - self.ee_x, body.y - self.ee_y)) > reach:
                continue
            body.x = float(np.clip(body.x + dx * gain, 0.12, 0.90))
            body.y = float(np.clip(body.y + dy * gain, 0.12, 0.70))
            delta_x = body.x - self.ee_x
            delta_y = body.y - self.ee_y
            dist = float(np.hypot(delta_x, delta_y))
            min_dist = body.radius + EE_RADIUS * 0.8
            if dist < 1e-6:
                norm = float(np.hypot(dx, dy)) + 1e-8
                delta_x, delta_y, dist = dx / norm, dy / norm, 1.0
            if dist < min_dist:
                scale = min_dist / dist
                body.x = float(np.clip(self.ee_x + delta_x * scale, 0.12, 0.90))
                body.y = float(np.clip(self.ee_y + delta_y * scale, 0.12, 0.70))
            self.events.append("push")

    def _check_success(self) -> bool:
        target = self._by_id(self.target_id)
        if target is None:
            return False
        if self.task in {"pick_place", "sort"}:
            inside = abs(target.x - BIN_XY[0]) < BIN_HALF[0] - 0.015 and abs(target.y - BIN_XY[1]) < BIN_HALF[1] - 0.015
            return inside and self.holding is None
        if self.task == "stack":
            support = next(body for body in self.bodies if body.role == "support")
            aligned = np.hypot(target.x - support.x, target.y - support.y) < 0.03
            stacked = target.z >= support.z + support.sz + target.sz - 0.02
            return bool(aligned and stacked and self.holding is None)
        if self.task == "push":
            return bool(np.hypot(target.x - ZONE_XY[0], target.y - ZONE_XY[1]) < ZONE_TOL)
        if self.task == "drawer":
            return target.x >= DRAWER_OPEN_X - 0.005
        return False

    def _goal_error(self) -> float | None:
        target = self._by_id(self.target_id)
        if target is None:
            return None
        if self.task in {"pick_place", "sort"}:
            return float(np.hypot(target.x - BIN_XY[0], target.y - BIN_XY[1]))
        if self.task == "stack":
            support = next(body for body in self.bodies if body.role == "support")
            return float(np.hypot(target.x - support.x, target.y - support.y))
        if self.task == "push":
            return float(np.hypot(target.x - ZONE_XY[0], target.y - ZONE_XY[1]))
        if self.task == "drawer":
            return float(max(0.0, DRAWER_OPEN_X - target.x))
        return None

    def _by_id(self, body_id: str | None) -> Body | None:
        if body_id is None:
            return None
        for body in self.bodies:
            if body.id == body_id:
                return body
        return None

    def _body_dict(self, body: Body) -> dict:
        return {
            "id": body.id,
            "kind": body.kind,
            "x": body.x,
            "y": body.y,
            "z": body.z,
            "sx": body.sx,
            "sy": body.sy,
            "sz": body.sz,
            "color": body.color,
            "role": body.role,
            "radius": body.radius,
            "graspable": body.graspable,
        }
