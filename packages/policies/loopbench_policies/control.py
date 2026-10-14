"""Reactive servo shared by the privileged oracle and the vision policy.

The controller is a phase machine, not a planner. Clearance and transport
speed are explicit skills the improvement step can turn on.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

DEFAULT_WORKSPACE = {"x": (0.08, 0.92), "y": (0.08, 0.74), "z": (0.02, 0.22)}
DEFAULT_BLOCK_RADIUS = 0.058


@dataclass
class CtrlBody:
    id: str
    x: float
    y: float
    z: float
    sx: float
    sy: float
    sz: float
    color: str
    role: str
    radius: float


class Controller:
    def __init__(
        self,
        *,
        clearance: bool = False,
        careful_transport: bool = False,
        workspace: dict | None = None,
        block_radius: float = DEFAULT_BLOCK_RADIUS,
    ) -> None:
        self.clearance = clearance
        self.careful_transport = careful_transport
        self.workspace = workspace or DEFAULT_WORKSPACE
        self.block_radius = block_radius
        self.phase = "approach"
        self.wait = 0
        self.retries = 0
        self.search_t = 0
        self._support_cache: tuple[float, float, float, float] | None = None

    def reset(self) -> None:
        self.phase = "approach"
        self.wait = 0
        self.retries = 0
        self.search_t = 0
        self._support_cache = None

    def configure(self, *, workspace: dict | None = None, block_radius: float | None = None) -> None:
        if workspace is not None:
            self.workspace = {key: tuple(value) for key, value in workspace.items()}
        if block_radius is not None:
            self.block_radius = block_radius

    def act(self, ee: np.ndarray, bodies: list[CtrlBody], holding: str | None, goal: dict) -> np.ndarray:
        if self.retries > 5 or self.phase == "giveup":
            self.phase = "giveup"
            return np.array([0.0, 0.0, 0.0, -1.0])
        kind = goal["kind"]
        if kind == "push":
            return self._push(ee, bodies, goal)
        if kind == "drawer":
            return self._drawer(ee, bodies, holding, goal)
        return self._manipulate(ee, bodies, holding, goal)

    def _manipulate(self, ee: np.ndarray, bodies: list[CtrlBody], holding: str | None, goal: dict) -> np.ndarray:
        target = _find_color(bodies, goal["target_color"])
        obstacles = [body for body in bodies if body.role == "obstacle"]
        if target is None and self.phase in {"approach", "descend", "search", "close"}:
            self.phase = "search"
            return self._search(ee)
        if self.phase == "search" and target is not None:
            self.phase = "approach"
        if self.phase in {"lift", "transit", "lower", "open"} and not holding:
            self.retries += 1
            self.phase = "approach"
            return self._servo(ee, (float(ee[0]), float(ee[1]), float(ee[2])), -1.0, False)

        gx, gy, gz, tol = self._goal_pose(bodies, target, goal, ee)
        holding_now = holding is not None

        if self.phase == "approach":
            assert target is not None
            dest = (target.x, target.y, 0.17)
            dest = self._maybe_clear(ee, dest, obstacles)
            direct = _close(dest[0], dest[1], target.x, target.y, 1e-4)
            if direct and _close(float(ee[0]), float(ee[1]), target.x, target.y, 0.016) and abs(float(ee[2]) - 0.17) < 0.03:
                self.phase = "descend"
            return self._servo(ee, dest, -1.0, False)

        if self.phase == "descend":
            assert target is not None
            dest = (target.x, target.y, target.z)
            if _close(float(ee[0]), float(ee[1]), target.x, target.y, 0.016) and abs(float(ee[2]) - target.z) < 0.018:
                self.phase = "close"
                self.wait = 0
            return self._servo(ee, dest, -1.0, False)

        if self.phase == "close":
            assert target is not None
            self.wait += 1
            if self.wait >= 3:
                self.phase = "verify"
            return self._servo(ee, (target.x, target.y, target.z), 1.0, False)

        if self.phase == "verify":
            if holding_now:
                self.phase = "lift"
            else:
                self.retries += 1
                self.phase = "approach"
                return self._servo(ee, (float(ee[0]), float(ee[1]), 0.17), -1.0, False)

        if self.phase == "lift":
            dest = (float(ee[0]), float(ee[1]), 0.17)
            if float(ee[2]) >= 0.155:
                self.phase = "transit"
            return self._servo(ee, dest, 1.0, True)

        if self.phase == "transit":
            dest = (gx, gy, 0.17)
            dest = self._maybe_clear(ee, dest, obstacles)
            direct = _close(dest[0], dest[1], gx, gy, 1e-4)
            if direct and _close(float(ee[0]), float(ee[1]), gx, gy, 0.02) and float(ee[2]) > 0.14:
                self.phase = "lower"
            return self._servo(ee, dest, 1.0, True)

        if self.phase == "lower":
            dest = (gx, gy, max(gz, 0.045))
            if _close(float(ee[0]), float(ee[1]), gx, gy, tol) and abs(float(ee[2]) - dest[2]) < 0.025:
                self.phase = "open"
                self.wait = 0
            return self._servo(ee, dest, 1.0, True)

        self.wait += 1
        return np.array([0.0, 0.0, 0.0, -1.0])

    def _goal_pose(self, bodies: list[CtrlBody], target: CtrlBody | None, goal: dict, ee: np.ndarray) -> tuple[float, float, float, float]:
        if goal["kind"] == "stack":
            support = _find_color(bodies, goal.get("support_color"))
            if support is not None:
                distance = float(np.hypot(support.x - float(ee[0]), support.y - float(ee[1])))
                # The carried cube occludes the support in a top-down view once we
                # get close. Keep the last clear sighting.
                if distance > 0.12 or self._support_cache is None:
                    self._support_cache = (support.x, support.y, support.z, support.sz)
            if self._support_cache is not None:
                sx, sy, sz, ssz = self._support_cache
                height = sz + ssz + (target.sz if target else 0.04)
                return sx, sy, height, 0.028
        return float(goal["x"]), float(goal["y"]), float(goal["z"]), float(goal["tol"])

    def _push(self, ee: np.ndarray, bodies: list[CtrlBody], goal: dict) -> np.ndarray:
        puck = _find_color(bodies, goal["target_color"])
        obstacles = [body for body in bodies if body.role == "obstacle"]
        if puck is None:
            self.phase = "search"
            return self._search(ee)
        vx, vy = float(goal["x"]) - puck.x, float(goal["y"]) - puck.y
        dist = float(np.hypot(vx, vy)) + 1e-8
        ux, uy = vx / dist, vy / dist
        rel = (float(ee[0]) - puck.x) * -ux + (float(ee[1]) - puck.y) * -uy
        lateral = abs((float(ee[0]) - puck.x) * -uy + (float(ee[1]) - puck.y) * ux)
        behind = rel > 0.02 and rel < 0.12 and lateral < 0.03 and abs(float(ee[2]) - puck.z) < 0.03
        touching = float(np.hypot(float(ee[0]) - puck.x, float(ee[1]) - puck.y)) < (puck.radius + 0.02)
        pushing = touching and lateral < 0.04 and rel > -0.01 and abs(float(ee[2]) - puck.z) < 0.03
        if behind or pushing:
            self.phase = "push"
            dest = (float(goal["x"]), float(goal["y"]), puck.z)
        else:
            self.phase = "align"
            dest = (puck.x - ux * 0.08, puck.y - uy * 0.08, puck.z)
        dest = self._maybe_clear(ee, dest, obstacles)
        return self._servo(ee, dest, -1.0, False)

    def _drawer(self, ee: np.ndarray, bodies: list[CtrlBody], holding: str | None, goal: dict) -> np.ndarray:
        drawer = _find_color(bodies, goal["target_color"])
        obstacles = [body for body in bodies if body.role == "obstacle"]
        if drawer is None and self.phase in {"approach", "descend", "search"}:
            self.phase = "search"
            return self._search(ee)
        if self.phase == "search" and drawer is not None:
            self.phase = "approach"
        if self.phase == "pull" and not holding:
            self.retries += 1
            self.phase = "approach"
        if self.phase == "approach":
            assert drawer is not None
            dest = self._maybe_clear(ee, (drawer.x, drawer.y, 0.16), obstacles)
            direct = _close(dest[0], dest[1], drawer.x, drawer.y, 1e-4)
            if direct and _close(float(ee[0]), float(ee[1]), drawer.x, drawer.y, 0.016) and abs(float(ee[2]) - 0.16) < 0.03:
                self.phase = "descend"
            return self._servo(ee, dest, -1.0, False)
        if self.phase == "descend":
            assert drawer is not None
            dest = (drawer.x, drawer.y, drawer.z)
            if _close(float(ee[0]), float(ee[1]), drawer.x, drawer.y, 0.016) and abs(float(ee[2]) - drawer.z) < 0.02:
                self.phase = "close"
                self.wait = 0
            return self._servo(ee, dest, -1.0, False)
        if self.phase == "close":
            assert drawer is not None
            self.wait += 1
            if self.wait >= 3:
                self.phase = "verify"
            return self._servo(ee, (drawer.x, drawer.y, drawer.z), 1.0, False)
        if self.phase == "verify":
            if holding:
                self.phase = "pull"
            else:
                self.retries += 1
                self.phase = "approach"
                return self._servo(ee, (float(ee[0]), float(ee[1]), 0.16), -1.0, False)
        if drawer is None:
            return np.zeros(4)
        dest = (float(goal["x"]), drawer.y, drawer.z)
        if drawer.x >= float(goal["x"]) - 0.012:
            self.phase = "done"
            return np.array([0.0, 0.0, 0.0, 1.0])
        self.phase = "pull"
        return self._servo(ee, dest, 1.0, True)

    def _search(self, ee: np.ndarray) -> np.ndarray:
        self.search_t += 1
        x = 0.24 + 0.52 * (0.5 + 0.5 * np.sin(self.search_t / 5.0))
        y = min(0.62, 0.18 + self.search_t * 0.012)
        return self._servo(ee, (float(x), float(y), 0.17), -1.0, False)

    def _maybe_clear(self, ee: np.ndarray, dest: tuple[float, float, float], obstacles: list[CtrlBody]) -> tuple[float, float, float]:
        if not self.clearance or not obstacles:
            return dest
        ex, ey = float(ee[0]), float(ee[1])
        blockers = [
            body
            for body in obstacles
            if _segment_hits(
                ex,
                ey,
                dest[0],
                dest[1],
                body.x,
                body.y,
                max(body.radius, self.block_radius),
            )
        ]
        if not blockers:
            return dest
        margin = self.block_radius + 0.06
        right = max(body.x for body in blockers) + margin
        left = min(body.x for body in blockers) - margin
        flank_x = right if abs(ex - right) <= abs(ex - left) else left
        low_x, high_x = self.workspace["x"]
        flank_x = float(np.clip(flank_x, low_x + 0.02, high_x - 0.02))
        if dest[1] >= ey:
            flank_y = max(body.y for body in blockers) + 0.05
        else:
            flank_y = min(body.y for body in blockers) - 0.05
        low_y, high_y = self.workspace["y"]
        flank_y = float(np.clip(flank_y, low_y + 0.02, high_y - 0.02))
        if float(np.hypot(ex - flank_x, ey - flank_y)) > 0.035:
            return (flank_x, flank_y, dest[2])
        return dest

    def _servo(self, ee: np.ndarray, dest: tuple[float, float, float], grip: float, transporting: bool) -> np.ndarray:
        limit = 0.02 if (transporting and self.careful_transport) else 0.045
        delta = [float(dest[i] - ee[i]) for i in range(3)]
        clipped = [float(np.clip(value, -limit, limit)) for value in delta]
        space = self.workspace
        proposed = [
            float(np.clip(ee[0] + clipped[0], *space["x"])),
            float(np.clip(ee[1] + clipped[1], *space["y"])),
            float(np.clip(ee[2] + clipped[2], *space["z"])),
        ]
        out = [proposed[i] - float(ee[i]) for i in range(3)]
        return np.array([out[0], out[1], out[2], grip], dtype=np.float64)


def _find_color(bodies: list[CtrlBody], color: str | None) -> CtrlBody | None:
    if color is None:
        return None
    matches = [body for body in bodies if body.color == color and body.role != "obstacle"]
    if not matches:
        return None
    return matches[0]


def _close(x: float, y: float, gx: float, gy: float, tol: float) -> bool:
    return bool(np.hypot(x - gx, y - gy) < tol)


def _first_hit(
    ax: float, ay: float, bx: float, by: float, obstacles: list[CtrlBody], block_radius: float
) -> CtrlBody | None:
    best = None
    best_d = 1e9
    for body in obstacles:
        radius = max(body.radius, block_radius)
        if _segment_hits(ax, ay, bx, by, body.x, body.y, radius):
            dist = float(np.hypot(body.x - ax, body.y - ay))
            if dist < best_d:
                best, best_d = body, dist
    return best


def _segment_hits(ax: float, ay: float, bx: float, by: float, cx: float, cy: float, radius: float) -> bool:
    abx, aby = bx - ax, by - ay
    length = abx * abx + aby * aby
    if length < 1e-10:
        return bool(np.hypot(ax - cx, ay - cy) < radius)
    t = max(0.0, min(1.0, ((cx - ax) * abx + (cy - ay) * aby) / length))
    px, py = ax + abx * t, ay + aby * t
    return bool(np.hypot(px - cx, py - cy) < radius)


def _detour(
    ax: float,
    ay: float,
    bx: float,
    by: float,
    body: CtrlBody,
    block_radius: float,
    workspace: dict,
) -> tuple[float, float]:
    dx, dy = bx - ax, by - ay
    norm = float(np.hypot(dx, dy)) + 1e-8
    px, py = -dy / norm, dx / norm
    mag = max(body.radius, block_radius) + 0.03
    options = ((body.x + px * mag, body.y + py * mag), (body.x - px * mag, body.y - py * mag))
    options = tuple(
        (
            float(np.clip(x, workspace["x"][0] + 0.01, workspace["x"][1] - 0.01)),
            float(np.clip(y, workspace["y"][0] + 0.01, workspace["y"][1] - 0.01)),
        )
        for x, y in options
    )
    return min(options, key=lambda item: np.hypot(item[0] - ax, item[1] - ay))
