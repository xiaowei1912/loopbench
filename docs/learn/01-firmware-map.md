# 01 从固件概念对照过来

先建立对照，再读代码。右边的英文是仓库里的标识，搜索时用英文。

| 你做过的 | 在 Loopbench 里 | 去哪看 |
| --- | --- | --- |
| 控制周期，一次 ISR | 一步。策略给动作，仿真推进一步 | `loopbench_evalkit/runner.py` 里的 `_run` |
| 传感器帧 | `observation.image`（俯视 RGB）和 `observation.state`（末端位置、夹爪） | 参考环境 `packages/sim-reference/.../env.py` |
| 执行器指令 | 长度至少为 4 的动作：平面增量、高度、夹爪 | `select_action` 的返回值 |
| 任务描述，例如工单上的一句话 | `task`，一条语言指令 | 观测里的 `task` 字段 |
| 看门狗超时 | 参考仿真最多 120 步，到点记 `truncated` | `constants.py` 的 `HORIZON` |
| 通过 / 失败标志 | `info["metrics"]` 里的 `success`，再被收成 `EpisodeTrace` | `loopbench_spec/schema.py` |
| 调试串口、JTAG 里的内部变量 | `info["privileged"]`：物体真值、相机偏移 | [ADR 0003](../adr/0003-privileged.md) |
| 量产固件，不能依赖调试口 | `vision_v1`，`needs_privileged = False` | `packages/policies/.../vision.py` |
| 金机或理想上界 | `oracle`，直接读真值，用来证明基准本身能被做完 | `packages/policies/.../oracle.py` |
| 产线标定工位 | `improve()`。标定阶段可以看真值，标定完参数冻进策略，再评测时调试口关掉 | `packages/policies/.../improve.py` |
| 温湿度、供电、振动这类 corner | 因素：`lighting`、`camera`、`clutter`、`friction`、`jitter`。值是名字，不是寄存器值 | `Factors`，[ADR 0004](../adr/0004-one-factor.md) |
| 一组测试向量 | `Suite`。`tabletop_probe` 是两任务、六格 | `packages/evalkit/.../suites.py` |
| 随机种子，为了复现 | `seed`。同一种子在参考仿真上像素相同 | 评测参数 `--seed` |
| 软件在环，算法在 PC 上跑、被测对象是模型 | 参考桌面。纯 NumPy，准静态，CI 里几秒到几十秒 | `packages/sim-reference` |
| 带接触和关节的在环模型 | MuJoCo 桌面。`mj_step`，CI 里会跑一条抓取放置 | `packages/sim-mujoco` |
| 硬件在环，流水线机器上没有那块板 | Isaac Lab、ManiSkill、LIBERO 等适配器。没装库就报不可用，API 返回 409 | `packages/bridges`，`docs/coverage.md` |
| HAL，应用不直接碰寄存器 | 仿真插件。评测器只调用 `make()` / `probe()` | `loopbench.simulators` 这一组 entry point |
| 模块之间禁止随意 include | `scripts/check_boundaries.py` 扫 import 行 | CI 的 `make test` 会先跑它 |
| 插件表、弱符号 | setuptools entry point。装上一个包，目录里就多一项 | `packages/*/pyproject.toml` |
| 一次测试用例 | 一条 episode：一个任务、一格因素、一颗种子 | `EpisodeSpec` |
| 测试报告 | `summary`：条数、成功数、成功率、按任务和按失败模式拆开 | 界面「记录」，或 `data/runs/` |
| CI job | `.github/workflows/ci.yml` 里的 `python` 和 `web` | [07](07-pipeline.md) |
| 缺治具就失败，而不是跳过并报绿 | 仿真或策略 `probe().available` 为假时，`POST /api/jobs` 返回 409 | `packages/api/.../app.py` |
| 协议版本号 | `loopbench.experiment/1`。结果里带着它，避免以后改了字段还拿旧记录对比 | `loopbench_spec/composition.py` |

## 三条线，分开记

固件工程里，驱动、控制律、测试脚本通常不写在同一个文件。这里也是三条线：

1. **仿真**产生观测和接触。它知道一米是多少、颜色的 RGB 是多少。
2. **策略**只消费观测，给出动作。它不应该把「箱子在 x = 0.76」写死。这些几何由仿真放进 `info["fixtures"]`。
3. **评测**决定跑哪些任务、哪些因素、哪颗种子，并把 trace 分类。它不 import 某一个仿真的模块。

训练是第四条线，不在这个仓库。权重留在 LeRobot、OpenVLA、GR00T、openpi 自己的环境里。评测只要求那个对象有 `select_action`。

## 一个容易混的词

「模型」在职位描述里指策略网络。在仿真里，MuJoCo 的 MJCF 也叫模型。本仓库的文档里：

- **策略**指决定动作的对象，包括 `oracle`、`vision_v1`，以及以后的 ACT、π0。
- **仿真**指把动作推进一步、给出观测的对象。
- **基准**指要跑的任务和因素格子，不指某一个网络。

## 做完再往下

能用自己的话讲完这三句再读 02：

- 一条 episode 是一次带步数上限的控制循环。
- `oracle` 走调试口，`vision_v1` 不走。
- 因素的值是名字。米和 RGB 属于仿真，不属于基准。
