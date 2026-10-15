# 企业评测平面

公开仓库里值得搬的是边界，不是源码。下面六项是 2026-10 对照过的项目。每一项只采用一条接缝，代码在这个仓库里重写，上游许可证下的实现不复制进来。

| 项目 | 地址 | 采用的接缝 | 明确不搬 |
| --- | --- | --- | --- |
| Isaac Lab-Arena | https://github.com/isaac-sim/IsaacLab-Arena | 场景 × 本体 × 任务，再由实验 YAML 把多次 run 收成一次评测 | OSMO 多机调度、Isaac 场景资产 |
| RoboVerse | https://github.com/RoboVerseOrg/RoboVerse | 每个仿真器一个 handler。上层只看见统一环境 | MetaSim 本体和它的任务库 |
| XPolicyLab | https://github.com/XPolicyLab/XPolicyLab | 策略进程和仿真进程分开。适配器只做 reset 和取动作 | 约 63 个策略的目录，以及他们的 WebSocket 栈 |
| vla-evaluation-harness | https://github.com/allenai/vla-evaluation-harness | 基准运行时和模型运行时隔离。种子、条数、策略、仿真写进协议 | 他们的基准 Docker 镜像 |
| LeRobot | https://github.com/huggingface/lerobot | 基准是 Gymnasium 环境加注册配置。结果从 episode 汇总到套件 | 数据集和训练脚本 |
| praxis-eval | https://github.com/Chaoqi-LIU/praxis-eval | 基准驱动可选安装，harness 拥有 rollout 和产物 | 远程集群执行器 |

界面上的「架构」页读 `GET /api/platform`，协议号和这张表来自同一份 `SOURCES`，避免文档和产品各写一套。

## 五个平面

1. **组合。** `EnvironmentDefinition` 有 `scene`、`embodiment`、`task`、`factors`。它能变成一格的 `Suite`，所以现有的 `evaluate` 不用分叉。参考桌面和 MuJoCo 的 `accepts()` 只接受 `tabletop` × `planar_gripper`。
2. **仿真 handler。** 已有的 `loopbench.simulators` 插件就是 handler。评测器调用 `make()`，如果对象有 `accepts` 再调用它。Isaac、ManiSkill、LIBERO、RoboCasa、RoboTwin 仍然是适配器，因素记在事件里，不在那些仿真里改写。
3. **策略进程。** `packages/transport` 用标准库 TCP，一行一个 JSON：`reset`、`act`、`close`。图像是 uint8 的 base64，不是嵌套数组。`loopbench policy-serve` 起服务。`RemotePolicy` 对评测器来说就是一个有 `reset` / `select_action` / `close` 的对象。
4. **实验。** `experiments/*.yaml` 的形状是 `name`、`shared`、`runs`。每个 run 恰好选择 `suite` 或 `environment` 其中一个。`endpoint` 存在时，动作来自那个进程，`policy` 只是标签。`loopbench experiment <path>` 和 `POST /api/experiments` 走同一个 `run_experiment`。
5. **协议。** 协议号是 `loopbench.experiment/1`。每条实验记录带上仿真、种子、每格条数、策略名、端点、场景和本体。`continue_on_error` 为真时，失败的 run 留下错误字符串，后面的 run 继续；否则停在第一个失败。

evalkit 不 import transport。谁打开策略，谁负责在 `needs_privileged` 上说真话。远程 oracle 必须把这个字段设为真，否则 runner 会剥掉 `privileged`，oracle 会直接报错。视觉策略保持关闭。

## 一条本地实验

```bash
loopbench experiment experiments/tabletop_smoke.yaml
```

同一份 `tabletop_smoke` 上并排跑 oracle 和 vision_v1。参考仿真，种子 0，每格 1 条。oracle 两条都成功。vision 在相机平移那一格会抓空，run 本身仍然成功结束，成功率写在 summary 里。

策略拆进程：

```bash
loopbench policy-serve --policy oracle --host 127.0.0.1 --port 43126
```

实验 run 里写 `endpoint: 127.0.0.1:43126` 和 `needs_privileged: true`。仿真留在评测进程，真值只在这个声明打开时过线。
