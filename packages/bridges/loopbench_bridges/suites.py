"""Suites whose tasks are the ones the matching simulator actually maps.

Cells stay in the shared factor vocabulary. These upstreams do not apply
camera=shifted inside their own scene randomizer; the driver records that
the factor was requested and not applied.
"""

from __future__ import annotations

from loopbench_spec.schema import Factors, Suite

NOMINAL = (Factors(),)


isaac_franka = Suite(
    name="isaac_franka",
    label="Isaac Franka",
    description="配对仿真器 isaac-lab。任务是 Lift、Stack、Open Drawer 三个官方 gym id。push 和 sort 没有对应的 Franka 环境。",
    tasks=("pick_place", "stack", "drawer"),
    cells=NOMINAL,
    upstream="Isaac Lab",
    upstream_url="https://isaac-sim.github.io/IsaacLab/main/source/overview/environments.html",
)

maniskill_v1 = Suite(
    name="maniskill_v1",
    label="ManiSkill",
    description="配对仿真器 maniskill。PickCube-v1、StackCube-v1、PushCube-v1、OpenCabinetDrawer-v1。",
    tasks=("pick_place", "stack", "push", "drawer"),
    cells=NOMINAL,
    upstream="ManiSkill",
    upstream_url="https://github.com/haosulab/ManiSkill",
)

libero_spatial = Suite(
    name="libero_spatial",
    label="LIBERO-Spatial",
    description="配对仿真器 libero。五个任务 id 映射到 libero_spatial 的前五个 task，语言来自 benchmark。",
    tasks=("pick_place", "stack", "push", "drawer", "sort"),
    cells=NOMINAL,
    upstream="LIBERO",
    upstream_url="https://github.com/Lifelong-Robot-Learning/LIBERO",
)

libero_object = Suite(
    name="libero_object",
    label="LIBERO-Object",
    description="配对仿真器 libero，默认基准 libero_object。OffScreenRenderEnv 读 bddl_file。",
    tasks=("pick_place", "stack", "push", "drawer", "sort"),
    cells=NOMINAL,
    upstream="LIBERO",
    upstream_url="https://github.com/Lifelong-Robot-Learning/LIBERO",
)

libero_goal = Suite(
    name="libero_goal",
    label="LIBERO-Goal",
    description="配对仿真器 libero。任务索引进 libero_goal。",
    tasks=("pick_place", "stack", "push", "drawer", "sort"),
    cells=NOMINAL,
    upstream="LIBERO",
    upstream_url="https://github.com/Lifelong-Robot-Learning/LIBERO",
)

libero_10 = Suite(
    name="libero_10",
    label="LIBERO-10",
    description="配对仿真器 libero。任务索引进 libero_10。π0.5 的 LIBERO checkpoint 是 pi05_libero。",
    tasks=("pick_place", "stack", "push", "drawer", "sort"),
    cells=NOMINAL,
    upstream="LIBERO",
    upstream_url="https://github.com/Lifelong-Robot-Learning/LIBERO",
)

robocasa_kitchen = Suite(
    name="robocasa_kitchen",
    label="RoboCasa Kitchen",
    description="配对仿真器 robocasa。PickPlaceCounterToCabinet、OpenDrawer、PickPlaceCounterToSink。没有叠放和推动的官方任务。",
    tasks=("pick_place", "drawer", "sort"),
    cells=NOMINAL,
    upstream="RoboCasa",
    upstream_url="https://github.com/robocasa/robocasa",
)

robotwin_v2 = Suite(
    name="robotwin_v2",
    label="RoboTwin 2.0",
    description="配对仿真器 robotwin。place_a2b_left、stack_blocks_two、open_microwave、pick_diverse_bottles。",
    tasks=("pick_place", "stack", "drawer", "sort"),
    cells=NOMINAL,
    upstream="RoboTwin",
    upstream_url="https://github.com/RoboTwin-Platform/RoboTwin",
)
