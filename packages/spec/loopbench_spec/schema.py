"""Scene factors and the benchmark objects every repo agrees on."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Factors(BaseModel):
    """One cell of a designed experiment.

    A one-factor cell changes exactly one field from the defaults.
    Values are names, not simulator parameters: each simulator decides what
    `camera=shifted` or `lighting=glare` means in its own units.
    """

    model_config = ConfigDict(frozen=True)

    clutter: int = 0
    friction: str = "nominal"
    lighting: str = "nominal"
    jitter: str = "low"
    camera: str = "nominal"

    def differs_from_nominal(self) -> dict[str, Any]:
        base = type(self)()
        data = self.model_dump()
        return {key: data[key] for key in data if data[key] != getattr(base, key)}

    def label(self) -> str:
        parts = [f"{key}={value}" for key, value in self.differs_from_nominal().items()]
        return ", ".join(parts) if parts else "nominal"


class Suite(BaseModel):
    """A benchmark shipped by any repository via the `loopbench.suites` entry point."""

    model_config = ConfigDict(frozen=True)

    name: str
    label: str
    description: str
    tasks: tuple[str, ...]
    cells: tuple[Factors, ...]
    upstream: str = "loopbench"
    upstream_url: str = ""


class EpisodeSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    task: str
    factors: Factors
    seed: int


class TaskInfo(BaseModel):
    """Task ids are the vocabulary suites and simulators share.

    A suite may name a task the active simulator does not implement. That is a
    runtime error from the simulator, not a reason to fork the suite package.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    label: str
    family: str
    instruction: str
    needs_grasp: bool
    upstream: str = ""
    upstream_url: str = ""


TASKS: dict[str, TaskInfo] = {
    "pick_place": TaskInfo(
        id="pick_place",
        label="抓取放置",
        family="LIBERO / ManiSkill",
        instruction="put the red cube into the bin",
        needs_grasp=True,
        upstream="ManiSkill PickCube, LIBERO object suite",
        upstream_url="https://github.com/haosulab/ManiSkill",
    ),
    "stack": TaskInfo(
        id="stack",
        label="叠放",
        family="ManiSkill",
        instruction="stack the green cube on the yellow cube",
        needs_grasp=True,
        upstream="ManiSkill StackCube",
        upstream_url="https://github.com/haosulab/ManiSkill",
    ),
    "push": TaskInfo(
        id="push",
        label="推入区域",
        family="LeRobot PushT",
        instruction="push the gray puck into the zone",
        needs_grasp=False,
        upstream="lerobot/pusht",
        upstream_url="https://github.com/huggingface/lerobot",
    ),
    "drawer": TaskInfo(
        id="drawer",
        label="拉开抽屉",
        family="RoboCasa",
        instruction="pull the drawer open by the handle",
        needs_grasp=True,
        upstream="robocasa",
        upstream_url="https://github.com/robocasa/robocasa",
    ),
    "sort": TaskInfo(
        id="sort",
        label="按颜色分拣",
        family="LIBERO-Object",
        instruction="put the {color} cube into the bin",
        needs_grasp=True,
        upstream="LIBERO-Object",
        upstream_url="https://github.com/Lifelong-Robot-Learning/LIBERO",
    ),
}


class EpisodeTrace(BaseModel):
    task: str
    success: bool
    steps: int
    path_length: float
    collisions: int
    slips: int
    grasp_attempts: int
    wrong_grasps: int
    ever_grasped_target: bool
    needs_grasp: bool
    goal_error: float | None = None
    events: list[str] = Field(default_factory=list)
