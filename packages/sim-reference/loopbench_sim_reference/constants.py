"""Geometry, colors, and fixture poses shared by the simulator and the asset library.

Policies may use the asset library (object size given a class). They may not read
live simulator state unless the eval runner marks them as privileged.
"""

from __future__ import annotations

RENDER_SIZE = 160
WORLD_X = 1.0
WORLD_Y = 0.80
HORIZON = 120

EE_START = (0.50, 0.14, 0.18)
EE_RADIUS = 0.016
WORKSPACE = {"x": (0.08, 0.92), "y": (0.08, 0.74), "z": (0.02, 0.22)}

CAMERA_SHIFT = (0.06, -0.045)

# Grasp gates. Low friction is still wide enough for a well-aligned servo;
# the low-friction failure mode is slip during fast transport, not the pinch itself.
GRASP_XY = {"low": 0.024, "nominal": 0.034, "high": 0.038}
GRASP_Z = 0.035

SLIP_STEP = 0.022
SLIP_LIMIT = 0.05

PILLAR_RADIUS = 0.042
BLOCK_RADIUS = PILLAR_RADIUS + EE_RADIUS

BIN_XY = (0.76, 0.42)
BIN_HALF = (0.09, 0.09)
ZONE_XY = (0.74, 0.42)
ZONE_TOL = 0.07
DRAWER_CLOSED_X = 0.57
DRAWER_OPEN_X = 0.72
DRAWER_Y = 0.40

FIDUCIALS = ((0.16, 0.70), (0.84, 0.70))
FIDUCIAL_RADIUS = 0.018

NOMINAL_RGB = {
    "red": (196, 58, 48),
    "green": (46, 140, 78),
    "blue": (46, 92, 176),
    "yellow": (214, 170, 42),
    "gray": (128, 132, 138),
    "wood": (168, 112, 64),
    "magenta": (206, 36, 164),
    "obstacle": (72, 80, 90),
}

BACKGROUND = {
    "nominal": (214, 206, 192),
    "dim": (92, 88, 80),
    "glare": (228, 222, 210),
}

# sx, sy, sz, radius. z of a resting object equals sz.
ASSETS = {
    "cube": {"sx": 0.040, "sy": 0.040, "sz": 0.040, "radius": 0.040},
    "puck": {"sx": 0.040, "sy": 0.040, "sz": 0.020, "radius": 0.040},
    "drawer": {"sx": 0.055, "sy": 0.050, "sz": 0.035, "radius": 0.055},
    "obstacle": {"sx": 0.042, "sy": 0.042, "sz": 0.20, "radius": BLOCK_RADIUS},
}

LAYOUT = {
    "pick_place": [("cube", "red", "target", 0.34, 0.42)],
    "stack": [
        ("cube", "yellow", "support", 0.30, 0.48),
        ("cube", "green", "target", 0.50, 0.34),
    ],
    "push": [("puck", "gray", "target", 0.36, 0.40)],
    "drawer": [("drawer", "wood", "target", DRAWER_CLOSED_X, DRAWER_Y)],
    "sort": [
        ("cube", "red", "option", 0.28, 0.50),
        ("cube", "green", "option", 0.48, 0.38),
        ("cube", "blue", "option", 0.32, 0.28),
    ],
}

SORT_COLORS = ("red", "green", "blue")

TASK_META = {
    "pick_place": {
        "label": "抓取放置",
        "family": "LIBERO / ManiSkill",
        "instruction": "put the red cube into the bin",
        "needs_grasp": True,
    },
    "stack": {
        "label": "叠放",
        "family": "ManiSkill",
        "instruction": "stack the green cube on the yellow cube",
        "needs_grasp": True,
    },
    "push": {
        "label": "推入区域",
        "family": "MetaWorld",
        "instruction": "push the gray puck into the zone",
        "needs_grasp": False,
    },
    "drawer": {
        "label": "拉开抽屉",
        "family": "RoboCasa",
        "instruction": "pull the drawer open by the handle",
        "needs_grasp": True,
    },
    "sort": {
        "label": "按颜色分拣",
        "family": "LIBERO",
        "instruction": "put the {color} cube into the bin",
        "needs_grasp": True,
    },
}

COLOR_WORDS = {
    "red": "红色",
    "green": "绿色",
    "blue": "蓝色",
    "yellow": "黄色",
    "gray": "灰色",
}


def apply_lighting(rgb: tuple[int, int, int], lighting: str, *, protect: bool = False) -> tuple[int, int, int]:
    if protect or lighting == "nominal":
        return rgb
    red, green, blue = rgb
    if lighting == "dim":
        return (int(red * 0.62), int(green * 0.62), int(blue * 0.62))
    lum = (red + green + blue) / 3.0
    return (
        min(255, int(lum * 0.62 + red * 0.38 + 34)),
        min(255, int(lum * 0.62 + green * 0.38 + 34)),
        min(255, int(lum * 0.62 + blue * 0.38 + 34)),
    )


def default_prototypes() -> dict[str, list[list[int]]]:
    return {name: [list(rgb)] for name, rgb in NOMINAL_RGB.items()}


def camera_offset_of(factors) -> tuple[float, float]:
    """Interpret the spec-level camera name in this simulator's meters."""

    if getattr(factors, "camera", None) == "shifted":
        return CAMERA_SHIFT
    return (0.0, 0.0)
