# 计划

Loopbench 要演示的是一条能产品化的评测闭环，不是再包一层某个仿真器。

职位里的工作是：让普通工程师在几分钟里走完模型、仿真、基准、评测、结果，并且能从失败回到环境和数据，再改进模型。长期形态是：

评测 → 理解失败 → 生成环境或数据 → 改进模型 → 再评测。

这个仓库先把闭环的接缝做成可以独立发布的包，再用一个不需要 GPU 的参考仿真把闭环跑通。Isaac Lab、MuJoCo、LIBERO 这些重依赖留在各自的上游仓库里，通过 entry point 接进来。

## 现在已经能跑的

- 契约包 `loopbench-spec`：任务词汇、因素名字、Suite、EpisodeTrace、entry point 注册表。
- 参考仿真 `Loopbench/Tabletop-v0`：Gymnasium Env，确定性，纯 NumPy。
- 两个策略：特权 oracle，以及不读真值的 `vision_v1`。`improve()` 产出 `vision_v2`。
- 评测、单因素归因、场景生成、闭环比较。
- 一个只依赖 spec 的示例基准 `tabletop_smoke`，用来证明新仓库不用改评测器。
- CLI、FastAPI、Next.js 评测台。
- 边界检查、pytest、GitHub Actions、Docker Compose。

## 刻意没做的

- 不把 Isaac Sim、Isaac Lab、MuJoCo、ManiSkill、LIBERO、RoboCasa、LeRobot 的任务代码 vendoring 进来。适配器只探测能不能 import，并写下真实的接入函数。
- 不训练 GR00T、π0、OpenVLA、ACT。策略接口对齐 LeRobot 的 `select_action`，`SelectActionAdapter` 可以把返回 Tensor 的对象接进来。权重和 CUDA 留在那些仓库。
- 不声称杂乱工况已经修好。参考探针里 `clutter=2` 只从 0% 回到 50%。

## 下一步如果要接真仿真

1. 新仓库依赖 `loopbench-spec` 和目标仿真器。
2. 实现 `Backend.make()`，返回 Gymnasium Env。观测键和 `info` 字段按 [扩展说明](extending.md)。
3. 在 `loopbench.simulators` 注册。
4. 用已有的 suite 跑 `loopbench eval`。任务 id 对不上时，由仿真器报错，而不是去改 suite 包。

策略仓库同样只注册 `loopbench.policies`。如果策略是 LeRobot 或 OpenVLA 那种 `select_action`，用 `loopbench_policies.bridge.SelectActionAdapter` 包一层，不必改评测器。
