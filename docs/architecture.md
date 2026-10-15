# 架构

评测器是一个不认识具体仿真的 harness。仿真、策略、基准都是装进来的插件。

```text
apps/web  --HTTP-->  loopbench-api  -->  loopbench-evalkit
                         |                    |
                         |                    | registry (entry points)
                         |                    v
                         |     simulators / policies / suites
                         |
                         +--> loopbench-transport   策略进程 (TCP JSON)
```

五个平面、实验 YAML 和协议号写在 [平台](platform.md)。API 源码不 import 仿真模块，也不 import 策略模块。策略如果在另一个进程，API 只打开 `RemotePolicy`。

API 进程安装了仿真和策略，这样 entry point 才存在，但源码里没有 `import loopbench_sim_reference`。

## 一次闭环

1. `registry.simulator` / `registry.policy` / `registry.suite` 按名字加载插件。
2. `evaluate` 创建环境。只有 `policy.needs_privileged` 为真时才 `expose_privileged=True`。否则 `public_info` 删掉 `privileged`。
3. 每个 episode：`reset(seed, options={task, factors})`，然后循环 `select_action(observation, info)` 和 `step`。
4. trace 写成 `EpisodeTrace`，`classify` 给失败模式。
5. `analyze` 做单因素切片和中文说明。
6. `generate_scenarios` 产生加压、反事实、标定三种场景，上限 24 条。
7. `plugin.improve(policy, report, backend.make)`。视觉策略在这里用特权相机采颜色，然后冻结进原型库。
8. 用同一个 suite、同一个 seed 再评一次。比较按 `(task, factors, seed)` 对齐，数找回和退步。

## 观测和动作

观测对齐 LeRobot 数据集里常见的键：

- `observation.image`：uint8，HWC
- `observation.state`：末端 xy、高度、夹爪
- `task`：语言指令

动作至少 4 维：平面增量、高度、夹爪。`SelectActionAdapter` 接受返回 Tensor 的对象，用来接 LeRobot 的 `PreTrainedPolicy.select_action`。

环境对齐 Gymnasium 1.0：

- `reset(*, seed, options) -> (obs, info)`
- `step(action) -> (obs, reward, terminated, truncated, info)`

Gym id：`Loopbench/Tabletop-v0`。

## info 里有什么

仿真必须公布策略和渲染都要用、但又不该写死在策略仓库里的量：

- `fixtures`：箱子、区域、抽屉、地标
- `materials`：未打光的物体颜色
- `assets`
- `camera_model`
- `control`：工作空间和 `block_radius`
- `metrics`：这一步的 EpisodeTrace 字段

`privileged` 里有物体真值和相机偏移。视觉策略的 `select_action` 不读它。标定发生在 `improve()`，那时 `make(expose_privileged=True)` 是显式的。

## 参考仿真里因素的含义

这些数只属于 `loopbench-sim-reference`，suite 看不见：

- 光照：dim 是亮度乘 0.62，glare 是往白里洗。
- 相机：`CAMERA_SHIFT = (0.06, -0.045)` 米。抓取门限大约 0.034 米，所以这个平移会让 v1 抓空。两个品红地标可以把平移解出来。
- 杂乱：柱子挡在直线上。
- 低摩擦：平面步长超过 0.022 米就开始打滑，累计超过 0.05 米则掉落，并把物体沿 x 再挪开 0.08 米，避免“滑进箱子也算成功”。

## 失败模式

分类只看 trace，不看第二套模型。优先级：滑落、抓错、碰撞且从未抓住、抓空、放置偏差、推动未入区、超时。

单因素说明目前会指出手眼平移、颜色恒常性、柱子几何、低摩擦搬运。高抖动如果没有掉点，会记成“闭环视觉对抖动是稳的”。

## HTTP

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| GET | `/api/health` | 存活 |
| GET | `/api/platform` | 协议号，以及采用了哪些公开项目的哪一条接缝 |
| GET | `/api/catalog` | 仿真、策略、套件、任务、上游探测 |
| POST | `/api/experiments` | 一份实验 JSON。仿真不可运行时返回 409，不启动任务 |
| POST | `/api/jobs` | `{kind: eval\|loop, suite, policy, simulator, episodes_per_cell, seed, capture_frames}` |
| GET | `/api/jobs/{id}` | 进度。任务在进程内的线程里跑 |
| GET | `/api/runs` | 评测摘要 |
| GET | `/api/runs/{id}` | 含 episode。eval 和闭环的改进前带 analysis |
| GET | `/api/loops` | 闭环摘要 |
| GET | `/api/loops/{id}` | 前后对照、归因、improve 笔记 |

闭环内部把两轮标成 `before` / `after`。落盘时这两个名字不当作 id，避免两次闭环互相覆盖。

界面在 `apps/web`，开发端口 43123，把 `/api` 重写到 43124。
