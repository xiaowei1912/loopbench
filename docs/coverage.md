# 覆盖了什么

职位里的每一项都有一个入口。入口分两种，不要混着读。

**可运行**：这个仓库的 CI 会真正步进。现在是参考桌面和 MuJoCo 桌面。

**适配器已接入**：插件调用上游自己的构造函数。库、资产和权重不在这个仓库里，没安装时任务会被 API 拒绝，不会假装跑过。

## 仿真平台

| 平台 | 状态 | 代码 |
| --- | --- | --- |
| Gymnasium 契约 | 可运行 | `reset` / `step` 五元组。参考环境和 MuJoCo 环境都登记了 gym id。 |
| 参考桌面 | 可运行 | `packages/sim-reference`。准静态，纯 NumPy。闭环探针的数字来自这里。 |
| MuJoCo | 可运行 | `packages/sim-mujoco`。`mj_step`，头顶相机用 `mujoco.Renderer`。抓取放置在 CI 里从抓起到放入箱子。夹爪是三轴滑动关节加 position 伺服，推动时打开碰撞。 |
| Isaac Lab | 适配器 | `gym.make("Isaac-Lift-Cube-Franka-v0" \| "Isaac-Stack-Cube-Franka-v0" \| "Isaac-Open-Drawer-Franka-v0")`，调用前 import `isaaclab_tasks`。push 和 sort 没有对应的 Franka 任务，适配器会拒绝。需要 Isaac Sim 的 GPU 环境，CI 不跑。 |

## 基准

| 基准 | 状态 | 官方调用 |
| --- | --- | --- |
| ManiSkill | 适配器 | `PickCube-v1`、`StackCube-v1`、`PushCube-v1`、`OpenCabinetDrawer-v1`，`obs_mode="rgb"`，`control_mode="pd_ee_delta_pose"`。 |
| LIBERO | 适配器 | `benchmark.get_benchmark_dict()` 加上 `OffScreenRenderEnv(bddl_file_name=...)`。套件有 spatial、object、goal、10。任务 id 映射到 suite 里的前几个 task，语言用 benchmark 自己的句子。 |
| RoboCasa | 适配器 | `gym.make("robocasa/PickPlaceCounterToCabinet")`、`robocasa/OpenDrawer`、`robocasa/PickPlaceCounterToSink`。gym id 失败时回退 `create_env(env_name="PnPCounterToCab")` 等短名。 |
| RoboTwin 2.0 | 适配器 | `import envs.<task>`，然后 `setup_demo`、`get_obs`、`take_action(..., action_type="qpos")`、`check_success`。映射到 `place_a2b_left`、`stack_blocks_two`、`open_microwave`、`pick_diverse_bottles`。 |

这些基准的因素名字会写进 trace 的 events（`factors_recorded_not_applied`）。它们自己的域随机不由 Loopbench 改写。

## 策略

| 策略 | 状态 | 官方调用 | 权重环境变量 |
| --- | --- | --- | --- |
| oracle、vision_v1 | 可运行 | 本仓库 | 无 |
| ACT | 适配器 | `ACTPolicy.from_pretrained(...).select_action` | `LOOPBENCH_ACT_CHECKPOINT` |
| OpenVLA | 适配器 | `AutoModelForVision2Seq.from_pretrained(..., trust_remote_code=True).predict_action` | `LOOPBENCH_OPENVLA_CHECKPOINT` |
| GR00T | 适配器 | `Gr00tPolicy(...).get_action` | `LOOPBENCH_GR00T_CHECKPOINT` |
| π0 | 适配器 | `get_config("pi0_droid")`，`policy.infer(example)["actions"]` | `LOOPBENCH_PI0_CHECKPOINT` |
| π0.5 | 适配器 | `get_config("pi05_droid")`，同一个 `infer`。LIBERO 微调是另一份 config `pi05_libero` | `LOOPBENCH_PI05_CHECKPOINT` |

π0 和 π0.5 是两个插件。动作块按时间展开，每步交给环境一行，不截成 4 维。4 维截断只属于参考桌面和 MuJoCo 桌面。

## CI 里会发生什么

`python` job 安装 `libosmesa6`，跑边界检查和 pytest。其中一条是 MuJoCo 抓取放置成功，以及用假的上游模块断言 gym id、BDDL 路径、`take_action` 和 `infer` 被调用。Isaac、LIBERO、GR00T 的权重不会在 CI 下载。
