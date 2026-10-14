"""MuJoCo tabletop with the Loopbench task ids.

The reference simulator is quasi-static NumPy. This one compiles an MJCF,
steps ``mujoco.mj_step``, and renders with ``mujoco.Renderer``. Task names
and factor names still come from ``loopbench-spec``. Meters live here.
"""

from __future__ import annotations

import os
from typing import Any

# The wheel's software renderer works on a machine without a display.
os.environ.setdefault("MUJOCO_GL", "osmesa")

import gymnasium as gym
import mujoco
import numpy as np
from gymnasium import spaces

from loopbench_spec.schema import TASKS, EpisodeTrace, Factors

RENDER_SIZE = 160
HORIZON = 160
WORKSPACE = {"x": (0.08, 0.92), "y": (0.08, 0.74), "z": (0.02, 0.28)}
BIN_XY = (0.76, 0.42)
BIN_HALF = 0.09
ZONE_XY = (0.74, 0.42)
ZONE_TOL = 0.07
DRAWER_OPEN_X = 0.72
CAMERA_SHIFT = (0.06, -0.045)

FRICTION = {"low": 0.08, "nominal": 0.8, "high": 1.4}
GRASP_XY = 0.03
GRASP_Z = 0.035

# name, color, role, x, y, half-extent z
LAYOUT: dict[str, list[tuple[str, str, str, float, float]]] = {
    "pick_place": [("red", "red", "target", 0.34, 0.42)],
    "stack": [("yellow", "yellow", "support", 0.30, 0.48), ("green", "green", "target", 0.50, 0.34)],
    "push": [("gray", "gray", "target", 0.36, 0.40)],
    "drawer": [("wood", "wood", "target", 0.57, 0.40)],
    "sort": [
        ("red", "red", "option", 0.28, 0.50),
        ("green", "green", "option", 0.48, 0.38),
        ("blue", "blue", "option", 0.32, 0.28),
    ],
}

RGBA = {
    "red": "0.77 0.23 0.19 1",
    "green": "0.18 0.55 0.31 1",
    "blue": "0.18 0.36 0.69 1",
    "yellow": "0.84 0.67 0.16 1",
    "gray": "0.50 0.52 0.54 1",
    "wood": "0.66 0.44 0.25 1",
    "obstacle": "0.28 0.31 0.35 1",
}

SORT_COLORS = ("red", "green", "blue")
FREE_BODIES = ("red", "green", "blue", "yellow", "gray", "wood", "pillar0", "pillar1")


def _xml() -> str:
    cubes = []
    for name in ("red", "green", "blue", "yellow", "gray", "wood"):
        half_z = "0.012" if name == "gray" else "0.02"
        mass = "0.04" if name == "gray" else "0.06"
        cubes.append(
            f"""
            <body name="{name}" pos="0 0 -1">
              <freejoint name="{name}_joint"/>
              <geom name="{name}_geom" type="box" size="0.02 0.02 {half_z}" mass="{mass}" rgba="{RGBA[name]}"/>
            </body>"""
        )
    pillars = []
    for name in ("pillar0", "pillar1"):
        pillars.append(
            f"""
            <body name="{name}" pos="2 0 -1">
              <freejoint name="{name}_joint"/>
              <geom name="{name}_geom" type="cylinder" size="0.03 0.08" mass="8" rgba="{RGBA["obstacle"]}"/>
            </body>"""
        )
    return f"""
    <mujoco model="loopbench_tabletop">
      <option timestep="0.004" gravity="0 0 -9.81" integrator="implicitfast"/>
      <visual>
        <global offwidth="256" offheight="256"/>
        <headlight diffuse="0.2 0.2 0.2"/>
      </visual>
      <asset>
        <texture name="grid" type="2d" builtin="checker" width="128" height="128" rgb1="0.84 0.81 0.75" rgb2="0.78 0.75 0.69"/>
        <material name="table" texture="grid" texrepeat="4 4"/>
      </asset>
      <worldbody>
        <light name="key" pos="0.5 0.4 1.4" dir="0 0 -1" diffuse="0.9 0.88 0.82"/>
        <camera name="overhead" pos="0.50 0.40 1.35" xyaxes="1 0 0 0 1 0" fovy="42"/>
        <geom name="table" type="box" size="0.62 0.50 0.02" pos="0.50 0.40 -0.02" material="table"/>
        {"".join(cubes)}
        {"".join(pillars)}
        <body name="gx" pos="0 0 0">
          <inertial pos="0 0 0" mass="0.05" diaginertia="0.0002 0.0002 0.0002"/>
          <joint name="gx" type="slide" axis="1 0 0" limited="true" range="0.05 0.95" damping="8"/>
          <body name="gy" pos="0 0 0">
            <inertial pos="0 0 0" mass="0.05" diaginertia="0.0002 0.0002 0.0002"/>
            <joint name="gy" type="slide" axis="0 1 0" limited="true" range="0.05 0.78" damping="8"/>
            <body name="gripper" pos="0 0 0">
              <joint name="gz" type="slide" axis="0 0 1" limited="true" range="0.02 0.30" damping="4"/>
              <geom name="gripper_geom" type="box" size="0.02 0.02 0.012" mass="0.2" rgba="0.15 0.15 0.16 1" contype="0" conaffinity="1"/>
            </body>
          </body>
        </body>
      </worldbody>
      <actuator>
        <position name="ax" joint="gx" kp="800" kv="30" ctrlrange="0.05 0.95"/>
        <position name="ay" joint="gy" kp="800" kv="30" ctrlrange="0.05 0.78"/>
        <position name="az" joint="gz" kp="800" kv="20" ctrlrange="0.02 0.30"/>
      </actuator>
    </mujoco>
    """


class MujocoTabletop(gym.Env):
    """``Loopbench/MuJoCo-Tabletop-v0``.

    ``options["task"]`` is a spec task id. ``options["factors"]`` uses the
    shared factor names. Privileged state is omitted unless this object was
    built with ``expose_privileged=True``.
    """

    metadata = {"render_modes": ["rgb_array"]}

    def __init__(self, *, expose_privileged: bool = False, render_size: int = RENDER_SIZE) -> None:
        super().__init__()
        self.expose_privileged = expose_privileged
        self.render_size = int(render_size)
        self.model = mujoco.MjModel.from_xml_string(_xml())
        self.data = mujoco.MjData(self.model)
        self.renderer = mujoco.Renderer(self.model, height=self.render_size, width=self.render_size)
        self.observation_space = spaces.Dict(
            {
                "observation.image": spaces.Box(0, 255, shape=(self.render_size, self.render_size, 3), dtype=np.uint8),
                "observation.state": spaces.Box(-np.inf, np.inf, shape=(4,), dtype=np.float32),
                "task": spaces.Text(max_length=240),
            }
        )
        self.action_space = spaces.Box(
            low=np.array([-0.05, -0.05, -0.05, -1.0], dtype=np.float32),
            high=np.array([0.05, 0.05, 0.05, 1.0], dtype=np.float32),
            dtype=np.float32,
        )
        self._qadr = {
            name: int(self.model.jnt_qposadr[mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, f"{name}_joint")])
            for name in FREE_BODIES
        }
        self._vadr = {
            name: int(self.model.jnt_dofadr[mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, f"{name}_joint")])
            for name in FREE_BODIES
        }
        self._geom = {
            name: int(mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_GEOM, f"{name}_geom"))
            for name in (*FREE_BODIES, "gripper")
        }
        self._cam = int(mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_CAMERA, "overhead"))
        self._light = int(mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_LIGHT, "key"))
        self._gadr = [
            int(self.model.jnt_qposadr[mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, name)])
            for name in ("gx", "gy", "gz")
        ]
        self._task = "pick_place"
        self._factors = Factors()
        self._language = ""
        self._target = "red"
        self._sort_color = "red"
        self._ee = np.zeros(3)
        self._holding: str | None = None
        self._hold_offset = np.zeros(3)
        self._grip = False
        self._step_i = 0
        self._path = 0.0
        self._success = False
        self._grasp_attempts = 0
        self._wrong = 0
        self._ever_target = False
        self._collisions = 0
        self._active: set[str] = set()

    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None):
        super().reset(seed=seed)
        options = options or {}
        task = str(options.get("task", "pick_place"))
        if task not in TASKS:
            raise KeyError(f"MuJoCo tabletop has no task {task!r}. Known: {sorted(TASKS)}")
        factors = options.get("factors") or {}
        self._factors = factors if isinstance(factors, Factors) else Factors.model_validate(factors)
        self._task = task
        rng = np.random.default_rng(0 if seed is None else int(seed))
        self._sort_color = SORT_COLORS[int(0 if seed is None else seed) % len(SORT_COLORS)]
        mujoco.mj_resetData(self.model, self.data)
        self._apply_appearance()
        self._park_all()
        sigma = 0.004 if self._factors.jitter == "low" else 0.012
        self._active = set()
        for name, _color, role, x, y in LAYOUT[task]:
            jx, jy = rng.normal(0, sigma, size=2)
            self._place(name, float(x + jx), float(y + jy), self._rest_z(name))
            self._active.add(name)
        if task == "sort":
            self._target = self._sort_color
        else:
            self._target = next(name for name, _c, role, _x, _y in LAYOUT[task] if role == "target")
        if self._factors.clutter:
            target = self._pos(self._target)
            count = 2 if self._factors.clutter >= 2 else 1
            for index, fraction in enumerate((0.42, 0.68)[:count]):
                name = f"pillar{index}"
                px = float(target[0] + fraction * (BIN_XY[0] - target[0]))
                py = float(target[1])
                self._place(name, px, py, 0.08)
                self._active.add(name)
        self._ee = np.array([0.50, 0.14, 0.18], dtype=np.float64)
        self._set_ee(self._ee, snap=True)
        self._holding = None
        self._grip = False
        self._step_i = 0
        self._path = 0.0
        self._success = False
        self._grasp_attempts = 0
        self._wrong = 0
        self._ever_target = False
        self._collisions = 0
        instruction = TASKS[task].instruction
        if task == "sort":
            instruction = instruction.format(color=self._sort_color)
        self._language = instruction
        mujoco.mj_forward(self.model, self.data)
        return self._obs(), self._info()

    def step(self, action):
        command = np.asarray(action, dtype=np.float64).reshape(-1)
        if command.size < 4:
            raise ValueError(f"MuJoCo tabletop expects 4 action numbers, got {command.size}.")
        delta = np.clip(command[:3], -0.05, 0.05)
        previous = self._ee.copy()
        proposed = self._ee + delta
        for axis, key in enumerate(("x", "y", "z")):
            low, high = WORKSPACE[key]
            proposed[axis] = float(np.clip(proposed[axis], low, high))
        grip = bool(command[3] > 0)
        if grip and not self._grip:
            self._grasp_attempts += 1
            self._try_grasp()
        if not grip:
            self._holding = None
        self._grip = grip
        gripper_geom = self._geom["gripper"]
        pushing = self._task == "push"
        # Both bits must be off. MuJoCo collides when either geom's contype
        # matches the other's conaffinity, so conaffinity=1 still hits the cube.
        self.model.geom_contype[gripper_geom] = 1 if pushing else 0
        self.model.geom_conaffinity[gripper_geom] = 1 if pushing else 0
        # Position servos track the command. Substeps let contact push the puck
        # instead of the gripper tunneling through it.
        self.data.ctrl[:3] = proposed
        for _ in range(12):
            self._enforce_hold()
            self._lock_idle()
            mujoco.mj_step(self.model, self.data)
            self._enforce_hold()
        self._ee = np.array([self.data.qpos[adr] for adr in self._gadr], dtype=np.float64)
        self._path += float(np.linalg.norm(self._ee - previous))
        self._count_contacts()
        self._step_i += 1
        self._success = self._check_success()
        terminated = self._success
        truncated = self._step_i >= HORIZON and not terminated
        reward = 1.0 if terminated else 0.0
        return self._obs(), reward, terminated, truncated, self._info()

    def render(self):
        return self._image()

    def close(self):
        self.renderer.close()
        super().close()

    def _apply_appearance(self) -> None:
        slide = FRICTION.get(self._factors.friction, FRICTION["nominal"])
        for name in ("red", "green", "blue", "yellow", "gray", "wood"):
            self.model.geom_friction[self._geom[name], 0] = slide
        cam = self.model.cam_pos[self._cam]
        cam[0] = 0.50 + (CAMERA_SHIFT[0] if self._factors.camera == "shifted" else 0.0)
        cam[1] = 0.40 + (CAMERA_SHIFT[1] if self._factors.camera == "shifted" else 0.0)
        diffuse = {"nominal": 0.9, "dim": 0.45, "glare": 1.4}.get(self._factors.lighting, 0.9)
        self.model.light_diffuse[self._light] = diffuse

    def _park_all(self) -> None:
        for index, name in enumerate(FREE_BODIES):
            self._place(name, 1.6 + 0.15 * index, -1.2, -0.8)

    def _set_ee(self, pos: np.ndarray, *, snap: bool) -> None:
        for adr, value in zip(self._gadr, pos, strict=True):
            self.data.qpos[adr] = float(value)
        self.data.ctrl[:3] = pos
        if snap:
            mujoco.mj_forward(self.model, self.data)

    def _place(self, name: str, x: float, y: float, z: float) -> None:
        adr = self._qadr[name]
        self.data.qpos[adr : adr + 3] = (x, y, z)
        self.data.qpos[adr + 3 : adr + 7] = (1, 0, 0, 0)
        vadr = self._vadr[name]
        self.data.qvel[vadr : vadr + 6] = 0

    def _pos(self, name: str) -> np.ndarray:
        adr = self._qadr[name]
        return np.array(self.data.qpos[adr : adr + 3], dtype=np.float64)

    def _rest_z(self, name: str) -> float:
        return 0.012 if name == "gray" else 0.02

    def _try_grasp(self) -> None:
        best_name = None
        best_dist = 1e9
        for name in self._active:
            if name.startswith("pillar"):
                continue
            pos = self._pos(name)
            dist = float(np.hypot(pos[0] - self._ee[0], pos[1] - self._ee[1]))
            if dist < best_dist and dist <= GRASP_XY and abs(float(pos[2] - self._ee[2])) <= GRASP_Z:
                best_dist = dist
                best_name = name
        if best_name is None:
            return
        self._holding = best_name
        self._hold_offset = self._pos(best_name) - self._ee
        if best_name == self._target:
            self._ever_target = True
        else:
            self._wrong += 1

    def _enforce_hold(self) -> None:
        if self._holding is None:
            return
        pos = self._ee + self._hold_offset
        self._place(self._holding, float(pos[0]), float(pos[1]), float(pos[2]))

    def _lock_idle(self) -> None:
        for index, name in enumerate(FREE_BODIES):
            if name not in self._active:
                self._place(name, 1.6 + 0.15 * index, -1.2, -0.8)
                continue
            if name == self._holding:
                continue
            if name.startswith("pillar") or name == "wood":
                pos = self._pos(name)
                self._place(name, float(pos[0]), float(pos[1]), self._rest_z(name) if name == "wood" else 0.08)

    def _count_contacts(self) -> None:
        for index in range(int(self.data.ncon)):
            contact = self.data.contact[index]
            names = []
            for geom in (int(contact.geom1), int(contact.geom2)):
                raw = mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_GEOM, geom) or ""
                names.append(raw.removesuffix("_geom"))
            if "gripper" in names and any(name.startswith("pillar") for name in names):
                self._collisions += 1

    def _check_success(self) -> bool:
        if self._task in {"pick_place", "sort"}:
            pos = self._pos(self._target)
            return bool(abs(pos[0] - BIN_XY[0]) <= BIN_HALF and abs(pos[1] - BIN_XY[1]) <= BIN_HALF and pos[2] < 0.08)
        if self._task == "stack":
            green = self._pos("green")
            yellow = self._pos("yellow")
            return bool(np.hypot(green[0] - yellow[0], green[1] - yellow[1]) < 0.03 and green[2] > yellow[2] + 0.02)
        if self._task == "push":
            pos = self._pos("gray")
            return bool(np.hypot(pos[0] - ZONE_XY[0], pos[1] - ZONE_XY[1]) <= ZONE_TOL and pos[2] < 0.05)
        if self._task == "drawer":
            return bool(self._pos("wood")[0] >= DRAWER_OPEN_X - 0.01)
        return False

    def _goal_error(self) -> float:
        if self._task in {"pick_place", "sort"}:
            pos = self._pos(self._target)
            return float(np.hypot(pos[0] - BIN_XY[0], pos[1] - BIN_XY[1]))
        if self._task == "stack":
            green = self._pos("green")
            yellow = self._pos("yellow")
            return float(np.hypot(green[0] - yellow[0], green[1] - yellow[1]))
        if self._task == "push":
            pos = self._pos("gray")
            return float(np.hypot(pos[0] - ZONE_XY[0], pos[1] - ZONE_XY[1]))
        if self._task == "drawer":
            return float(max(0.0, DRAWER_OPEN_X - self._pos("wood")[0]))
        return 0.0

    def _image(self) -> np.ndarray:
        self.renderer.update_scene(self.data, camera="overhead")
        image = self.renderer.render()
        if image.dtype != np.uint8:
            image = np.clip(image, 0, 255).astype(np.uint8)
        return image

    def _obs(self) -> dict[str, Any]:
        return {
            "observation.image": self._image(),
            "observation.state": np.asarray([*self._ee, 1.0 if self._grip else 0.0], dtype=np.float32),
            "task": self._language,
        }

    def _body_dict(self, name: str, role: str, color: str) -> dict[str, Any]:
        pos = self._pos(name)
        half_z = 0.012 if name == "gray" else (0.08 if name.startswith("pillar") else 0.02)
        return {
            "id": name,
            "x": float(pos[0]),
            "y": float(pos[1]),
            "z": float(pos[2]),
            "sx": 0.03 if name.startswith("pillar") else 0.02,
            "sy": 0.03 if name.startswith("pillar") else 0.02,
            "sz": half_z,
            "color": color,
            "role": role,
            "radius": 0.03 if name.startswith("pillar") else 0.02,
        }

    def _info(self) -> dict[str, Any]:
        bodies = []
        for name, color, role, _x, _y in LAYOUT[self._task]:
            use_role = role
            if self._task == "sort":
                use_role = "target" if name == self._sort_color else "distractor"
            bodies.append(self._body_dict(name, use_role, color))
        if self._factors.clutter:
            count = 2 if self._factors.clutter >= 2 else 1
            for index in range(count):
                bodies.append(self._body_dict(f"pillar{index}", "obstacle", "obstacle"))
        trace = EpisodeTrace(
            task=self._task,
            success=self._success,
            steps=self._step_i,
            path_length=self._path,
            collisions=self._collisions,
            slips=0,
            grasp_attempts=self._grasp_attempts,
            wrong_grasps=self._wrong,
            ever_grasped_target=self._ever_target,
            needs_grasp=TASKS[self._task].needs_grasp,
            goal_error=self._goal_error(),
            events=["mujoco"],
        )
        info: dict[str, Any] = {
            "task_id": self._task,
            "language": self._language,
            "fixtures": {
                "bin": {"x": BIN_XY[0], "y": BIN_XY[1], "half": BIN_HALF},
                "zone": {"x": ZONE_XY[0], "y": ZONE_XY[1], "tol": ZONE_TOL},
                "drawer_open_x": DRAWER_OPEN_X,
                "drawer_y": 0.40,
                "stack": {"target_color": "green", "support_color": "yellow"},
                "fiducials": [],
            },
            "materials": {name: [int(float(channel) * 255) for channel in RGBA[name].split()[:3]] for name in RGBA},
            "assets": {},
            "camera_model": {"size": self.render_size, "shift": list(CAMERA_SHIFT)},
            "control": {
                "workspace": {axis: list(bounds) for axis, bounds in WORKSPACE.items()},
                "block_radius": 0.048,
            },
            "metrics": trace.model_dump(),
        }
        if self.expose_privileged:
            info["privileged"] = {
                "ee": (float(self._ee[0]), float(self._ee[1]), float(self._ee[2]), 1.0 if self._grip else 0.0),
                "holding": self._holding,
                "bodies": bodies,
                "factors": self._factors.model_dump(),
                "camera_offset": list(CAMERA_SHIFT if self._factors.camera == "shifted" else (0.0, 0.0)),
                "task": self._task,
                "target_id": self._target,
                "target_color": self._sort_color if self._task == "sort" else self._target,
                "language": self._language,
            }
        return info


def register_gym() -> str:
    env_id = "Loopbench/MuJoCo-Tabletop-v0"
    if env_id not in gym.registry:
        gym.register(id=env_id, entry_point="loopbench_sim_mujoco.env:MujocoTabletop")
    return env_id
