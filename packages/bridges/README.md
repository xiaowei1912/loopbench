# loopbench-bridges

Isaac Lab、ManiSkill、LIBERO、RoboCasa、RoboTwin 的仿真入口，以及 ACT、OpenVLA、GR00T、π0、π0.5 的策略入口。

安装这个包不会下载那些库，也不会下载权重。`probe()` 看 import 和 checkpoint 环境变量。`make()` 调用上游自己的构造函数：

| 插件 | 调用 |
| --- | --- |
| isaac-lab | `gym.make("Isaac-Lift-Cube-Franka-v0")` 等，先 import `isaaclab_tasks` |
| maniskill | `gym.make("PickCube-v1", obs_mode="rgb", control_mode="pd_ee_delta_pose")` |
| libero | `benchmark.get_benchmark_dict()` + `OffScreenRenderEnv` |
| robocasa | `gym.make("robocasa/PickPlaceCounterToCabinet")`，失败再 `create_env` |
| robotwin | `envs.<task>.setup_demo` / `take_action` / `check_success` |
| act | `ACTPolicy.from_pretrained` + `select_action` |
| openvla | `AutoModelForVision2Seq.predict_action` |
| gr00t | `Gr00tPolicy.get_action` |
| pi0 | `get_config("pi0_droid")` + `policy.infer` |
| pi05 | `get_config("pi05_droid")` + `policy.infer` |

π0 和 π0.5 是两个插件、两套 checkpoint。因素名字会记进 trace，但这些上游环境自己的域随机不由 Loopbench 改写。
