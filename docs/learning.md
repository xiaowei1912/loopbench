# 学习路径

按职位里的工作往下读。每一节都说明 Loopbench 里哪段代码对应它，以及上游仓库在哪里。这个 demo 跑通的是接缝和参考桌面，不是那些仓库的 GPU 训练。

## 1. 仿真、训练、评测流水线

先分清三条线，不要合成一个脚本。

- 仿真产生观测和接触。参考实现在 `packages/sim-reference`。
- 策略只消费观测。`packages/policies/loopbench_policies/vision.py` 的 `select_action`。
- 评测编排种子、因素和汇总。`packages/evalkit/loopbench_evalkit/runner.py`。

训练不在这个仓库。LeRobot 的训练循环和 `PreTrainedPolicy` 在 <https://github.com/huggingface/lerobot>。接入点是 `select_action`，说明在 <https://huggingface.co/docs/lerobot/bring_your_own_policies>。

## 2. Isaac Sim / Isaac Lab 和 MuJoCo

Isaac Lab 用 Gymnasium 注册管理式环境：

`gym.register(id=..., entry_point="isaaclab.envs:ManagerBasedRLEnv", kwargs={"env_cfg_entry_point": ...})`

文档：<https://isaac-sim.github.io/IsaacLab/main/source/tutorials/03_envs/register_rl_env_gym.html>

仓库：<https://github.com/isaac-sim/IsaacLab>

Isaac Lab-Arena 把场景、本体和任务拆开再组合，用来规模化评测：<https://github.com/isaac-sim/IsaacLab-Arena>。Loopbench 的对应物是 `loopbench_spec.composition.EnvironmentDefinition`，仿真器用 `accepts` 拒绝自己编译不了的一对。实验 YAML 在 `experiments/`。说明在 `docs/platform.md`。

MuJoCo：<https://github.com/google-deepmind/mujoco>

Loopbench 里 MuJoCo 是可运行的第二个仿真，代码在 `packages/sim-mujoco`。Isaac Lab 的适配器在 `packages/bridges/loopbench_bridges/simulators.py` 的 `open_isaac`，调用 `gym.make("Isaac-Lift-Cube-Franka-v0")` 之前会 import `isaaclab_tasks`。没装 Isaac Sim 时界面标成「适配器已接入」，API 返回 409。对照表在 `docs/coverage.md`。

## 3. RoboTwin、RoboVerse、RoboCasa、LIBERO、ManiSkill

这些是基准和场景资产，不是又一个策略网络。

| 项目 | 和本仓库任务词汇的关系 | 地址 |
| --- | --- | --- |
| ManiSkill | pick_place、stack | <https://github.com/haosulab/ManiSkill> |
| LIBERO | pick_place、sort，语言和 BDDL | <https://github.com/Lifelong-Robot-Learning/LIBERO> |
| RoboCasa | drawer，厨房操作 | <https://github.com/robocasa/robocasa> |
| robosuite | LIBERO 和 RoboCasa 下面的仿真栈 | <https://github.com/ARISE-Initiative/robosuite> |
| RoboTwin 2.0 | 双臂、干净和随机两套设置 | <https://github.com/RoboTwin-Platform/RoboTwin> |
| RoboVerse | 多仿真统一的数据与评测 | <https://github.com/RoboVerseOrg/RoboVerse> |

LIBERO 的用法是 `get_benchmark_dict()[suite].get_task(i)` 拿出语言和 `bddl_file`，再交给 `OffScreenRenderEnv`。ManiSkill 是 `gym.make("PickCube-v1")`。这些字符串写在 `packages/adapters/loopbench_adapters/catalog.py`，方便对照，不在这里执行。

## 4. XPolicyLab

XPolicyLab 把「N 个策略 × M 个环境」收成「一个策略适配器 + 一个环境客户端」。策略服务和环境通过 websocket 分开，Isaac Sim 可以在一台机器，VLA 在另一台。

- 仓库：<https://github.com/XPolicyLab/XPolicyLab>
- 说明：<https://xpolicylab.github.io/>
- RoboTwin 里的用法：<https://robotwin-platform.github.io/doc/usage/xpolicylab.html>

Loopbench 的 entry point 是同一类问题的小版本：评测器不 import 策略仓库。策略进程用 `loopbench policy-serve`，线上是 TCP 的 JSON 行（`reset` / `act` / `close`），实现在 `packages/transport`。没有搬他们的 WebSocket 栈和策略目录。真的要评 GR00T 或 π0，那个进程里装权重，评测进程只拿到动作。

## 5. GR00T、π0 / π0.5、OpenVLA、ACT

| 策略 | 地址 | 在这里怎么接 |
| --- | --- | --- |
| NVIDIA Isaac GR00T | <https://github.com/NVIDIA/Isaac-GR00T> | 独立环境和权重。动作对上之后包进 `select_action`。 |
| π0 / π0.5（openpi） | <https://github.com/Physical-Intelligence/openpi> | 同上。不要把 JAX 依赖装进评测器。 |
| OpenVLA | <https://github.com/openvla/openvla> | `SelectActionAdapter` 收 Tensor。 |
| ACT | LeRobot 里的 `act` 策略 | 同一个 `select_action`。 |

本仓库的 `vision_v1` 不是这些模型的替代品。它是一个会在光照、相机、摩擦、杂乱上以可解释的方式失败的伺服，用来把归因和再评测跑通。

## 6. 失败分析和自动生成场景

读 `packages/evalkit/loopbench_evalkit/analysis.py` 和 `scenarios.py`。

单因素格子只改一个因素。delta 相对全名义工况。交互格留在 episode 表里，不写进那条结论。这是为了避免「又暗又偏相机」被同时算进两个原因。

生成的场景有三种：

- stress：在已经塌的格子上换种子
- counterfactual：同一颗种子，把那个因素拨回名义，用来核对是不是它
- calibration：光照扫描，当作带标签的采集，不计入得分

`vision` 的 `improve()` 用的就是标定这一路：特权相机只在采集时打开，原型冻结之后再评测不再读真值。

## 7. 把开源项目产品化

产品化在这里的意思是：目录、进度、落盘、空状态和失败说明，而不是再写一个训练框架。

界面五件事：选已安装的插件、看进度、读切片、对照闭环前后、读评测平面。后端页把「没装 Isaac」显示成未安装，而不是假装跑过。架构页列出五个平面和协议号。

扩展页和 `packages/example-suite` 给下一个人留了抄写模板。
