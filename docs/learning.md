# 学习文档

这套文档写给有嵌入式和 CI/CD 经验、还没做过机器人评测的人。不要求你训过模型，也不要求你有 GPU。

Loopbench 在这台机器上能跑完的是一条评测闭环：模型进仿真，仿真按基准出结果，失败被归到一个场景因素，策略改一版，同一套基准再评一次。Isaac、大模型权重不在这个仓库里。学完入门，你应该能自己把这条闭环跑通，并读懂一次失败。学完深入，你应该能接一个新的仿真或策略，并知道哪些上游仓库值得读。

## 怎么读

入门按 01 到 07 的顺序。每一章末尾有「做完再往下」。做完 07，你能独立跑通闭环、读一条失败记录、看懂 CI 在守什么。

深入从 10 开始，可以按手头的工作跳着读。上游地图放在最后，它是索引，不是第一天的教材。

| 章节 | 你会拿到什么 |
| --- | --- |
| [01 从固件概念对照过来](learn/01-firmware-map.md) | 一张表：控制周期、传感器、看门狗、HAL、corner、CI job 在这个仓库里叫什么 |
| [02 第一天下午](learn/02-first-afternoon.md) | 装好、跑通 `tabletop_smoke`、在界面上看到一次成功和一次失败 |
| [03 一条 episode](learn/03-one-episode.md) | `reset` / `step` / `select_action` 按时间展开，对应到文件 |
| [04 工况和失败](learn/04-corners-and-failures.md) | 因素格子、单因素归因、七种失败模式、探针上的实测数字 |
| [05 真值是调试口](learn/05-debug-port.md) | `privileged`、oracle、标定，以及为什么量产策略不能读真值 |
| [06 包就是固件分层](learn/06-modules.md) | 依赖方向、entry point、怎么加一个只依赖契约的基准 |
| [07 你已经会的流水线](learn/07-pipeline.md) | GitHub Actions、Docker、409 门禁，以及它和 HIL 的关系 |
| [10 两个仿真](learn/10-simulators.md) | 参考桌面和 MuJoCo 差在哪，Gymnasium 契约长什么样 |
| [11 基准](learn/11-benchmarks.md) | ManiSkill、LIBERO、RoboCasa、RoboTwin 各测什么，本仓库接到哪一层 |
| [12 策略和 VLA](learn/12-policies.md) | 从颜色伺服到 ACT、OpenVLA、GR00T、π0，权重为什么不进仓库 |
| [13 闭环拆开](learn/13-closed-loop.md) | 评测、归因、生成场景、改进、再评测，以及 25% 到 92% 怎么读 |
| [14 企业评测平面](learn/14-planes.md) | 场景 × 本体 × 任务、实验 YAML、策略进程、协议号 |
| [15 读仓库的顺序](learn/15-read-the-repo.md) | 文件清单：先读哪份，哪份可以先跳过 |
| [术语](learn/glossary.md) | 英文标识和中文对照 |
| [练习](learn/exercises.md) | 七个不需要 GPU 的练习，文末有对照结果 |
| [上游地图](learn/upstream.md) | 职位里那些 GitHub 仓库，和本仓库的对应位置 |

工程文档仍然分开：

- 怎么把服务跑起来：[运行手册](runbook.md)
- 模块边界和安装顺序：[仓库地图](repositories.md)
- 五个平面的来源：[平台](platform.md)
- 哪些平台是可运行、哪些只是适配器：[覆盖](coverage.md)
- 加仿真或加基准的合同：[扩展](extending.md)

## 你已经会的东西

嵌入式里你负责过「传感器进来、控制律算出执行器指令、超时要停、量产固件不能依赖调试口」。这里的一条 episode 就是这个循环，周期不是微秒级中断，而是仿真里的一步。

CI 里你负责过「每次提交都跑同一套检查，缺设备的测试不要假装通过」。这里的 GitHub Actions 守的是参考桌面和 MuJoCo。Isaac 没装时 API 返回 409，和「HIL 机架不在这条流水线上，就不要报绿」是同一件事。
