"""A third-party suite. This package is the template for a new benchmark repo."""

from loopbench_spec.schema import Factors, Suite

smoke = Suite(
    name="tabletop_smoke",
    label="Smoke",
    description="示例仓库：只依赖 spec，复用参考仿真已经实现的 pick_place，不改仿真代码。",
    tasks=("pick_place",),
    cells=(Factors(), Factors(camera="shifted")),
    upstream="example-suite",
)
