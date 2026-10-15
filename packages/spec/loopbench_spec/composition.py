"""Composition and experiment contracts.

These names follow the split used by Isaac Lab-Arena (scene, embodiment, task,
experiment YAML) without importing Isaac. A simulator decides whether it can
compile a given pair. A suite is still the benchmark grid; an environment
definition is one cell of that grid with an explicit scene and embodiment.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from loopbench_spec.schema import Factors, Suite

PROTOCOL = "loopbench.experiment/1"

# What was adopted from each public project. The code in this repo is ours;
# these records are the architectural sources, not vendored modules.
SOURCES: tuple[dict[str, str], ...] = (
    {
        "id": "isaaclab-arena",
        "url": "https://github.com/isaac-sim/IsaacLab-Arena",
        "adopted": "场景、本体、任务分开编译；实验 YAML 把多次 run 收成一次评测。",
    },
    {
        "id": "roboverse",
        "url": "https://github.com/RoboVerseOrg/RoboVerse",
        "adopted": "每个仿真器一个 handler。上层只看见统一的任务环境，不看见后端。",
    },
    {
        "id": "xpolicylab",
        "url": "https://github.com/XPolicyLab/XPolicyLab",
        "adopted": "策略进程和仿真进程分开。适配器只做 reset 和取动作。",
    },
    {
        "id": "vla-evaluation-harness",
        "url": "https://github.com/allenai/vla-evaluation-harness",
        "adopted": "基准运行时和模型运行时隔离，并把种子、条数、策略、仿真写进协议。",
    },
    {
        "id": "lerobot",
        "url": "https://github.com/huggingface/lerobot",
        "adopted": "基准是 Gymnasium 环境加注册配置。结果按 episode、任务、套件往上汇总。",
    },
    {
        "id": "praxis-eval",
        "url": "https://github.com/Chaoqi-LIU/praxis-eval",
        "adopted": "基准驱动和远程策略是可选安装，评测包自己拥有 rollout 和产物。",
    },
)


class EnvironmentDefinition(BaseModel):
    """One compiled environment: scene × embodiment × task."""

    model_config = ConfigDict(frozen=True)

    name: str
    scene: str
    embodiment: str
    task: str
    factors: Factors = Field(default_factory=Factors)

    def to_suite(self) -> Suite:
        return Suite(
            name=self.name,
            label=self.name,
            description=f"{self.scene} × {self.embodiment} × {self.task}",
            tasks=(self.task,),
            cells=(self.factors,),
            upstream="composition",
        )


class Rollout(BaseModel):
    """Settings shared by every run in an experiment. A run may override them."""

    model_config = ConfigDict(frozen=True)

    simulator: str = "reference"
    seed: int = 0
    episodes_per_cell: int = 1
    continue_on_error: bool = False


class RunSpec(BaseModel):
    """One named evaluation inside an experiment.

    `suite` selects an installed benchmark. `environment` is a single
    composition cell. `endpoint` is host:port of a policy process; when it is
    set, the policy name is only a label and the actions come from that process.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    policy: str
    suite: str | None = None
    environment: EnvironmentDefinition | None = None
    endpoint: str | None = None
    needs_privileged: bool | None = None
    simulator: str | None = None
    seed: int | None = None
    episodes_per_cell: int | None = None

    @model_validator(mode="after")
    def _one_target(self) -> RunSpec:
        if (self.suite is None) == (self.environment is None):
            raise ValueError(f"Run {self.name!r} needs exactly one of suite or environment.")
        return self


class Experiment(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    shared: Rollout = Field(default_factory=Rollout)
    runs: tuple[RunSpec, ...]

    def resolved(self, run: RunSpec) -> dict[str, Any]:
        return {
            "simulator": run.simulator or self.shared.simulator,
            "seed": self.shared.seed if run.seed is None else run.seed,
            "episodes_per_cell": self.shared.episodes_per_cell if run.episodes_per_cell is None else run.episodes_per_cell,
        }
