"""Closed-loop color servo.

The method name `select_action` matches LeRobot's `PreTrainedPolicy`.
Perception reads the image plus the asset library and fixture poses published
in `info`. It does not read `info["privileged"]`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from loopbench_policies.control import Controller, CtrlBody
from loopbench_spec.projection import px_to_world

OBJECT_COLORS = ("red", "green", "blue", "yellow", "gray", "wood")
SORT_COLORS = ("red", "green", "blue")


@dataclass
class VisionConfig:
    name: str = "vision_v1"
    online_calibration: bool = False
    clearance: bool = False
    careful_transport: bool = False
    threshold: float = 40.0
    prototypes: dict[str, list[list[int]]] | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "online_calibration": self.online_calibration,
            "clearance": self.clearance,
            "careful_transport": self.careful_transport,
            "threshold": self.threshold,
            "prototypes": self.prototypes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> VisionConfig:
        prototypes = data.get("prototypes")
        return cls(
            name=str(data.get("name", "vision")),
            online_calibration=bool(data.get("online_calibration", False)),
            clearance=bool(data.get("clearance", False)),
            careful_transport=bool(data.get("careful_transport", False)),
            threshold=float(data.get("threshold", 40.0)),
            prototypes=None
            if prototypes is None
            else {key: [list(map(int, item)) for item in value] for key, value in prototypes.items()},
        )


@dataclass
class Blob:
    label: str
    u: float
    v: float
    count: int
    x: float
    y: float


class VisionPolicy:
    name = "vision_v1"
    needs_privileged = False

    def __init__(self, config: VisionConfig | None = None) -> None:
        self.config = config or VisionConfig()
        self.name = self.config.name
        self.controller = Controller(
            clearance=self.config.clearance,
            careful_transport=self.config.careful_transport,
        )
        self.phase = "approach"
        self._prototypes: dict[str, list[list[int]]] | None = self.config.prototypes

    def reset(self) -> None:
        self.controller.clearance = self.config.clearance
        self.controller.careful_transport = self.config.careful_transport
        self.controller.reset()
        self.phase = "approach"
        self._prototypes = self.config.prototypes

    def select_action(self, observation: dict, info: dict | None = None) -> np.ndarray:
        if info is None:
            raise RuntimeError("VisionPolicy needs fixture and material info from the environment.")
        self.controller.configure(
            workspace=info.get("control", {}).get("workspace"),
            block_radius=info.get("control", {}).get("block_radius"),
        )
        if self._prototypes is None:
            self._prototypes = {name: [list(rgb)] for name, rgb in info["materials"].items()}
        camera = (0.0, 0.0)
        if self.config.online_calibration:
            estimated = estimate_camera(observation["observation.image"], self._prototypes, self.config.threshold, info)
            if estimated is not None:
                camera = estimated
        bodies = perceive(
            observation["observation.image"],
            self._prototypes,
            self.config.threshold,
            camera,
            info,
            include_obstacles=self.config.clearance,
        )
        holding = infer_holding(observation["observation.state"], bodies)
        goal = goal_for(info["task_id"], observation["task"], info["fixtures"])
        action = self.controller.act(observation["observation.state"], bodies, holding, goal)
        self.phase = self.controller.phase
        return action


def goal_for(task: str, language: str, fixtures: dict) -> dict:
    if task == "pick_place":
        return _place(fixtures, "red")
    if task == "sort":
        color = next((name for name in SORT_COLORS if name in language), "red")
        return _place(fixtures, color)
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
        return {"kind": "push", "x": zone["x"], "y": zone["y"], "z": 0.02, "tol": zone["tol"], "target_color": "gray"}
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


def _place(fixtures: dict, color: str) -> dict:
    bin_pose = fixtures["bin"]
    return {
        "kind": "place",
        "x": bin_pose["x"],
        "y": bin_pose["y"],
        "z": 0.05,
        "tol": bin_pose["half"] * 0.35,
        "target_color": color,
    }


def perceive(image, prototypes, threshold, camera, info, *, include_obstacles: bool) -> list[CtrlBody]:
    labels = list(OBJECT_COLORS)
    if include_obstacles:
        labels.append("obstacle")
    model = info["camera_model"]
    blobs = detect_blobs(image, prototypes, threshold, labels, camera, model)
    bodies: list[CtrlBody] = []
    block = float(info["control"]["block_radius"])
    for blob in blobs:
        asset = info["assets"].get(blob.label)
        if asset is None:
            continue
        if blob.label == "obstacle":
            bodies.append(
                CtrlBody(
                    id=f"obstacle-{len(bodies)}",
                    x=blob.x,
                    y=blob.y,
                    z=0.1,
                    sx=asset["sx"],
                    sy=asset["sy"],
                    sz=asset["sz"],
                    color="obstacle",
                    role="obstacle",
                    radius=block,
                )
            )
            continue
        bodies.append(
            CtrlBody(
                id=f"{blob.label}-seen",
                x=blob.x,
                y=blob.y,
                z=float(asset["sz"]),
                sx=float(asset["sx"]),
                sy=float(asset["sy"]),
                sz=float(asset["sz"]),
                color=blob.label,
                role="object",
                radius=float(asset["radius"]),
            )
        )
    return bodies


def infer_holding(proprio: np.ndarray, bodies: list[CtrlBody]) -> str | None:
    if float(proprio[3]) < 0.5:
        return None
    best = None
    best_d = 1e9
    for body in bodies:
        if body.role == "obstacle":
            continue
        dist = float(np.hypot(body.x - proprio[0], body.y - proprio[1]))
        if dist < 0.045 and dist < best_d:
            best, best_d = body, dist
    return None if best is None else best.id


def estimate_camera(image, prototypes, threshold, info) -> tuple[float, float] | None:
    model = info["camera_model"]
    blobs = detect_blobs(image, prototypes, threshold, ["magenta"], (0.0, 0.0), model)
    fiducials = info["fixtures"]["fiducials"]
    if len(blobs) < 2 or len(fiducials) < 2:
        return None
    ordered = sorted(blobs, key=lambda blob: blob.u)
    left, right = ordered[0], ordered[-1]
    dx1 = fiducials[0][0] - left.x
    dx2 = fiducials[1][0] - right.x
    dy1 = fiducials[0][1] - left.y
    dy2 = fiducials[1][1] - right.y
    if abs(dx1 - dx2) > 0.04 or abs(dy1 - dy2) > 0.04:
        return None
    return ((dx1 + dx2) / 2.0, (dy1 + dy2) / 2.0)


def detect_blobs(image, prototypes, threshold, labels, camera, model) -> list[Blob]:
    proto_rgb = []
    proto_label = []
    for label in labels:
        for rgb in prototypes.get(label, []):
            proto_rgb.append(np.asarray(rgb, dtype=np.float32))
            proto_label.append(label)
    if not proto_rgb:
        return []
    flat = image.reshape(-1, 3).astype(np.float32)
    protos = np.stack(proto_rgb, axis=0)
    dist = np.linalg.norm(flat[:, None, :] - protos[None, :, :], axis=2)
    best = dist.argmin(axis=1)
    best_d = dist.min(axis=1)
    label_ids = {label: index for index, label in enumerate(labels)}
    chosen = np.array([label_ids[proto_label[index]] for index in best], dtype=np.int16)
    assigned = np.full(flat.shape[0], -1, dtype=np.int16)
    assigned[best_d < threshold] = chosen[best_d < threshold]
    mask = assigned.reshape(image.shape[:2])
    blobs: list[Blob] = []
    size = int(model["size"])
    world_x = float(model["world_x"])
    world_y = float(model["world_y"])
    for label in labels:
        for u, v, count in _components(mask == label_ids[label]):
            x, y = px_to_world(u, v, camera[0], camera[1], size=size, world_x=world_x, world_y=world_y)
            blobs.append(Blob(label=label, u=u, v=v, count=count, x=x, y=y))
    return blobs


def _components(mask: np.ndarray, min_count: int = 8) -> list[tuple[float, float, int]]:
    if not np.any(mask):
        return []
    height, width = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    ys, xs = np.where(mask)
    found: list[tuple[float, float, int]] = []
    for y0, x0 in zip(ys.tolist(), xs.tolist()):
        if visited[y0, x0]:
            continue
        stack = [(y0, x0)]
        visited[y0, x0] = True
        cells: list[tuple[int, int]] = []
        while stack:
            y, x = stack.pop()
            cells.append((y, x))
            for ny in range(y - 1, y + 2):
                if ny < 0 or ny >= height:
                    continue
                for nx in range(x - 1, x + 2):
                    if nx < 0 or nx >= width or visited[ny, nx] or not mask[ny, nx]:
                        continue
                    visited[ny, nx] = True
                    stack.append((ny, nx))
        if len(cells) < min_count:
            continue
        arr = np.asarray(cells, dtype=np.float64)
        found.append((float(arr[:, 1].mean()), float(arr[:, 0].mean()), len(cells)))
    return found
