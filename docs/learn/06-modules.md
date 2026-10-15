# 06 包就是固件分层

一块板子的代码通常分成寄存器、驱动、服务、应用。上层不 include 某个芯片的头文件，否则换 MCU 时应用要重写。Loopbench 用同一种分层，单位是可以单独 `pip install` 的包。

## 谁可以调用谁

| 包 | 角色 | 可以依赖 | 不可以依赖 |
| --- | --- | --- | --- |
| `packages/spec` | 寄存器手册和测试项 ID。任务名、因素名、trace 字段 | pydantic | 仿真、策略、评测 |
| `packages/sim-reference` | 准静态桌面 | spec、Gymnasium、NumPy | 策略、评测 |
| `packages/sim-mujoco` | MuJoCo 桌面 | spec、Gymnasium、MuJoCo | 策略、评测、bridges |
| `packages/policies` | oracle、视觉伺服、标定 | spec、NumPy | 仿真、评测 |
| `packages/transport` | 策略进程的套接字 | NumPy | 仿真、策略、评测 |
| `packages/evalkit` | 跑 episode、归因、闭环、实验 | spec、NumPy、Pillow、PyYAML | 仿真、策略、transport |
| `packages/bridges` | 调用上游官方构造函数 | spec、NumPy | 本仓库的仿真和策略实现 |
| `packages/adapters` | 探测上游能不能 import | spec | 仿真、策略、评测 |
| `packages/example-suite` | 给新基准抄的最小例子 | spec | 其它一切 |
| `packages/api` | HTTP | spec、evalkit、transport，安装时带上插件 | 源码里不 import 仿真和策略模块 |
| `packages/cli` | 命令行 | api、evalkit、spec、transport | 仿真内部 |

评测器要拿到仿真时，不写 `import loopbench_sim_reference`。它问注册表：`simulator("reference")`。注册表读的是 setuptools entry point，和「链接时从插件表取出驱动」同类。

四组入口：

- `loopbench.simulators`
- `loopbench.policies`
- `loopbench.suites`
- `loopbench.adapters`

`scripts/check_boundaries.py` 只扫描含 `import` 或 `import_module` 的代码行。注释里提到另一个包的名字是允许的，适配器的说明文字靠这个。CI 里 `make test` 会先跑这个脚本。

这些包现在在同一个 git 仓库里，是为了一次克隆就能跑。依赖写的是分发名 `loopbench-spec>=0.1`，不写磁盘路径。以后拆成多个仓库，pyproject 不用改。地图在 [repositories.md](../repositories.md)。

## 加一个基准，不动评测器

`packages/example-suite` 注册了 `tabletop_smoke`。它只依赖 spec，复用参考仿真已经会做的 `pick_place`。评测器没有为它改过一行。

你自己的基准仓库最少是：

```python
from loopbench_spec.schema import Factors, Suite

smoke = Suite(
    name="tabletop_smoke",
    label="Smoke",
    description="只依赖 spec 的示例基准。",
    tasks=("pick_place",),
    cells=(Factors(), Factors(camera="shifted")),
    upstream="example-suite",
)
```

```toml
[project.entry-points."loopbench.suites"]
tabletop_smoke = "loopbench_example_suite:smoke"
```

`tasks` 里的字符串必须是 spec 里已有的 id：`pick_place`、`stack`、`push`、`drawer`、`sort`。仿真没实现某个任务时，在 `reset` 里报错。不要为了一个仿真去改套件的词汇，否则别的仿真的记录对不齐。

`Factors` 只接受名字。不要在套件里写 `0.06` 米或一组 RGB。

完整的仿真插件合同在 [extending.md](../extending.md)。入门阶段把 `tabletop_smoke` 的文件读一遍就够。

## 做完再往下

打开 `packages/example-suite/pyproject.toml`，找到 entry point 那一段。然后读 07，看 CI 怎样保证这些包没有互相 import。
