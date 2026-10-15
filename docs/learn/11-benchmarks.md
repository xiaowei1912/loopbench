# 11 基准

基准是别人已经设计好的一套测试向量：哪些任务、哪些场景、成功怎么判。它不是另一个神经网络。

本仓库自己的基准是 `tabletop_probe`、`tabletop_mini`、`tabletop_v1`、`tabletop_smoke`。外面的基准通过 `packages/bridges` 调用官方构造函数。库不在仓库里时，状态是适配器，API 拒绝开跑。

## 任务词汇是合同

| id | 在参考桌面上 | 公开基准里常见的对应 |
| --- | --- | --- |
| `pick_place` | 红块放进箱子 | ManiSkill `PickCube`，LIBERO 的物体操作 |
| `stack` | 绿块叠到黄块上 | ManiSkill `StackCube` |
| `push` | 把冰球推进区域 | LeRobot 的 PushT 这一类 |
| `drawer` | 把抽屉拉开 | RoboCasa 的开抽屉 |
| `sort` | 按颜色把块放进箱子 | LIBERO-Object 这一类 |

套件引用这些 id。某个仿真没有对应任务时，适配器拒绝，不改 id 的拼写。

## 五个外部基准

| 基准 | 官方调用长什么样 | 本仓库没接上的部分 |
| --- | --- | --- |
| [ManiSkill](https://github.com/haosulab/ManiSkill) | `gym.make("PickCube-v1")` 等，`obs_mode="rgb"`，`control_mode="pd_ee_delta_pose"` | 他们的资产和 GPU 环境 |
| [LIBERO](https://github.com/Lifelong-Robot-Learning/LIBERO) | `benchmark.get_benchmark_dict()[name]()`，再 `OffScreenRenderEnv(bddl_file_name=...)` | BDDL 场景文件。套件有 spatial、object、goal、10 |
| [RoboCasa](https://github.com/robocasa/robocasa) | `gym.make("robocasa/PickPlaceCounterToCabinet")` 等。失败时回退短名 `create_env` | 厨房资产。没有和 stack、push 对齐的任务 |
| [RoboTwin 2.0](https://github.com/RoboTwin-Platform/RoboTwin) | `import envs.<task>`，然后 `setup_demo`、`take_action`、`check_success` | 双臂机器和他们的随机化。push 没有映射 |
| [RoboVerse](https://github.com/RoboVerseOrg/RoboVerse) | 多仿真统一的一层，叫 MetaSim | 没有把 MetaSim 拷进仓库。采用的是「一个仿真一个 handler」这条结构 |

LIBERO 的任务下标在适配器里按 `pick_place=0` 到 `sort=4` 映射，超出任务数就取模。语言用基准自己的句子，不用参考桌面的句子。

RoboTwin 的映射是：`pick_place` → `place_a2b_left`，`stack` → `stack_blocks_two`，`drawer` → `open_microwave`，`sort` → `pick_diverse_bottles`。适配器只在那个 `envs` 包看起来真是 RoboTwin 时才认它，因为 `envs` 这个名字太常见。

这些仿真上的因素名字会写进 trace 的事件 `factors_recorded_not_applied`。意思是：记录里有 `camera=shifted` 这个测试项，但那个仿真没有按参考桌面的 6 厘米去改相机。它们自己的随机化仍由它们自己管。读外部基准的分数时，不要和参考桌面的单因素表直接相减。

## 套件规模

| 名字 | 任务 | 格子 | 用途 |
| --- | --- | --- | --- |
| `tabletop_smoke` | 只有 pick_place | 名义、相机平移 | 安装是否成功。example-suite 提供 |
| `tabletop_probe` | pick_place、stack | 六个单因素 | 闭环演示。种子 0、每格 1 条时是 12 条 episode |
| `tabletop_mini` | 五个任务 | 单因素扫描，含杂乱 1、高摩擦、高抖动 | 产品默认档 |
| `tabletop_v1` | 五个任务 | Mini 再加上两格交互 | 交互格不进入归因 delta |

外部套件名包括 `isaac_franka`、`maniskill_v1`、`libero_spatial`、`libero_object`、`libero_goal`、`libero_10`、`robocasa_kitchen`、`robotwin_v2`。它们出现在目录里，不出现在 CPU 的 CI 步进里。

## 读的时候看什么

1. `packages/evalkit/loopbench_evalkit/suites.py` 里 `probe` 的 `tasks` 和 `cells`。
2. `packages/example-suite` 整个目录，很短。
3. `packages/bridges/loopbench_bridges/simulators.py` 里一个 `open_*` 函数。建议从 `open_libero` 或 `open_maniskill` 开始，看它怎样把官方环境收成统一的 `reset` / `step`。
4. `docs/coverage.md` 的表。以那份表为准，不要凭记忆补官方 id。

## 这一章不要求你做的事

不要求把 LIBERO 的 BDDL 跑起来。要求你能回答：任务 id 属于哪个包，因素的米制属于哪个包，外部基准的分数为什么不能和参考探针的 92% 画在同一条曲线上。
