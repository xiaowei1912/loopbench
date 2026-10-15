# 15 读仓库的顺序

不要从 `apps/web` 开始，也不要先克隆 Isaac。下面按「先能改对，再看产品壳」排列。时间是在已经做完入门 01 到 07 的前提下估的。

## 第一遍，大约两个小时

| 顺序 | 文件 | 看什么 | 可以跳过 |
| --- | --- | --- | --- |
| 1 | `docs/learning.md` | 你现在的位置 | |
| 2 | `packages/spec/loopbench_spec/schema.py` | `Factors`、`Suite`、`EpisodeTrace`、`TASKS` | pydantic 的配置细节 |
| 3 | `packages/evalkit/loopbench_evalkit/runner.py` | `evaluate`、`_run` | 关键帧的 PNG 编码 |
| 4 | `packages/evalkit/loopbench_evalkit/analysis.py` | `classify`、`_is_one_factor` | 文案字符串可以后读 |
| 5 | `packages/sim-reference/loopbench_sim_reference/constants.py` | 前 40 行的数 | `LAYOUT` 先看 pick_place 一行 |
| 6 | `packages/policies/loopbench_policies/vision.py` | `needs_privileged` 和 `select_action` | 连通域的全部分支 |
| 7 | `packages/policies/loopbench_policies/improve.py` | `improve_vision` 的前 40 行 | 采样像素的循环 |
| 8 | `tests/test_packages.py` | 测试的名字。测试名字就是行为规格 | 先不改测试 |
| 9 | `.github/workflows/ci.yml` | 两个 job | |

读完跑：

```bash
loopbench eval --suite tabletop_smoke --policy oracle --seed 0
loopbench eval --suite tabletop_smoke --policy vision_v1 --seed 0
```

## 第二遍，按任务选

接仿真或想看接触：

- `packages/sim-mujoco/loopbench_sim_mujoco/env.py`
- `tests/test_upstream.py` 里 MuJoCo 那几条
- [10 两个仿真](10-simulators.md)

接外部基准：

- `docs/coverage.md`
- `packages/bridges/loopbench_bridges/simulators.py` 里一个 `open_*`
- [11 基准](11-benchmarks.md)

接带权重的策略：

- `packages/bridges/loopbench_bridges/policies.py`
- `packages/policies/loopbench_policies/bridge.py`
- [12 策略和 VLA](12-policies.md)

讲清探针或改归因：

- `packages/evalkit/loopbench_evalkit/loop.py`
- `packages/evalkit/loopbench_evalkit/scenarios.py`
- [13 闭环拆开](13-closed-loop.md)

把评测交给别人或拆进程：

- `experiments/tabletop_smoke.yaml`
- `packages/spec/loopbench_spec/composition.py`
- `packages/transport/loopbench_transport/wire.py`
- [14 企业评测平面](14-planes.md)

改界面：

- `apps/web/src/app/evaluate/page.tsx`
- `apps/web/src/app/architecture/page.tsx`
- `apps/web/src/lib/types.ts`

界面只通过 HTTP 说话。改字段时先改 API 的 JSON，再改 `types.ts`。

## 上游仓库，按这个深度读

每一项都先读 README 和「怎么创建一个环境 / 怎么调用策略」，不要先读训练脚本。

| 顺序 | 仓库 | 第一遍读什么 | 先不要读 |
| --- | --- | --- | --- |
| 1 | [Gymnasium 的 Env API](https://gymnasium.farama.org/api/env/) | `reset` 和 `step` 的返回值 | 全部封装好的算法库 |
| 2 | [LeRobot 接入策略](https://huggingface.co/docs/lerobot/bring_your_own_policies) | `select_action` 的位置 | 训练循环 |
| 3 | [MuJoCo](https://github.com/google-deepmind/mujoco) | 官方 getting started 里的一步仿真 | 全部插件 |
| 4 | [ManiSkill](https://github.com/haosulab/ManiSkill) | `PickCube-v1` 的 README 示例 | 全部任务列表 |
| 5 | [LIBERO](https://github.com/Lifelong-Robot-Learning/LIBERO) | `get_benchmark_dict` 和 BDDL 路径怎么交给环境 | 终身学习的论文实验设置 |
| 6 | [Isaac Lab 注册环境](https://isaac-sim.github.io/IsaacLab/main/source/tutorials/03_envs/register_rl_env_gym.html) | `gym.register` 那一页 | 在没 GPU 的机器上安装 Isaac Sim |
| 7 | [Isaac Lab-Arena](https://github.com/isaac-sim/IsaacLab-Arena) | 场景、本体、任务、实验 YAML 这四个词 | OSMO |
| 8 | [XPolicyLab](https://github.com/XPolicyLab/XPolicyLab) | 策略适配器和环境客户端为什么分开 | 他们的策略目录 |
| 9 | [openpi](https://github.com/Physical-Intelligence/openpi) | `pi0_droid` 和 `pi05_droid` 是两个 config | JAX 训练 |
| 10 | [OpenVLA](https://github.com/openvla/openvla) | `predict_action` | 微调全流程 |
| 11 | [Isaac-GR00T](https://github.com/NVIDIA/Isaac-GR00T) | `Gr00tPolicy.get_action` | 数据集下载 |
| 12 | [RoboCasa](https://github.com/robocasa/robocasa)、[RoboTwin](https://github.com/RoboTwin-Platform/RoboTwin)、[RoboVerse](https://github.com/RoboVerseOrg/RoboVerse) | README 里的一条创建环境的命令 | 资产管线 |

对应到本仓库哪一行，集中在 [上游地图](upstream.md)。

## 改代码时的检查

```bash
python3 scripts/check_boundaries.py
MUJOCO_GL=osmesa python3 -m pytest tests -q
```

改了页面再跑 `apps/web` 里的 `npm run build`。提交前看 CI 的两个 job。不要把 `data/`、权重或令牌提交进去。
