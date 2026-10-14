"""Benchmark suites registered through ``loopbench.suites``."""

from __future__ import annotations

from loopbench_spec.schema import TASKS, EpisodeSpec, Factors, Suite

NOMINAL = Factors()

PROBE_CELLS = (
    NOMINAL,
    Factors(lighting="glare"),
    Factors(lighting="dim"),
    Factors(camera="shifted"),
    Factors(clutter=2),
    Factors(friction="low"),
)

MINI_CELLS = (
    NOMINAL,
    Factors(lighting="dim"),
    Factors(lighting="glare"),
    Factors(camera="shifted"),
    Factors(clutter=1),
    Factors(clutter=2),
    Factors(friction="low"),
    Factors(friction="high"),
    Factors(jitter="high"),
)

V1_CELLS = (
    *MINI_CELLS,
    Factors(lighting="glare", camera="shifted"),
    Factors(clutter=2, friction="low"),
)

probe = Suite(
    name="tabletop_probe",
    label="Probe",
    description="两任务、六格的闭环探针。测试和一键演示用它，几十秒内出结论。",
    tasks=("pick_place", "stack"),
    cells=PROBE_CELLS,
    upstream="Loopbench reference",
)
mini = Suite(
    name="tabletop_mini",
    label="Tabletop Mini",
    description="五任务的单因素扫描。产品默认档，覆盖光照、相机、杂乱、摩擦和抖动。",
    tasks=("pick_place", "stack", "push", "drawer", "sort"),
    cells=MINI_CELLS,
    upstream="LIBERO-style one-factor sweep",
    upstream_url="https://github.com/Lifelong-Robot-Learning/LIBERO",
)
v1 = Suite(
    name="tabletop_v1",
    label="Tabletop v1",
    description="完整设计实验，在 Mini 上增加光照×相机和杂乱×摩擦两个交互格。",
    tasks=("pick_place", "stack", "push", "drawer", "sort"),
    cells=V1_CELLS,
    upstream="LIBERO + factorial interaction cells",
    upstream_url="https://github.com/Lifelong-Robot-Learning/LIBERO",
)


def iter_episodes(suite: Suite, episodes_per_cell: int, base_seed: int) -> list[EpisodeSpec]:
    if episodes_per_cell < 1:
        raise ValueError("episodes_per_cell must be >= 1")
    specs: list[EpisodeSpec] = []
    cursor = 0
    for task in suite.tasks:
        for cell in suite.cells:
            for offset in range(episodes_per_cell):
                specs.append(EpisodeSpec(task=task, factors=cell, seed=base_seed + cursor + offset * 17))
                cursor += 1
            cursor += 3
    return specs


def task_catalog() -> list[dict]:
    return [task.model_dump() for task in TASKS.values()]
