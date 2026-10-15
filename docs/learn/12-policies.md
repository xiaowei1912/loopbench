# 12 策略和 VLA

策略是「观测进去、动作出来」的对象。嵌入式里最接近的是控制律。这一章从你已经能读的视觉伺服讲到职位里的几个大模型，并说明本仓库接到哪一层就停。

## 本仓库里的两个策略

`vision_v1` 在图像里按颜色找连通区域，把像素换成桌面坐标，交给一个分阶段控制器：接近、下降、闭合、抬起、搬运、松开。这就是相机加伺服，没有训练。

它会按设计失败：

- 光照一变，固定阈值对不上颜色
- 相机一偏，坐标偏得超过抓取门限
- 直线上有柱子，路径撞上去
- 低摩擦时搬得太快，物体滑掉

`improve()` 把这些杠杆打开，得到 `vision_v2`。细节在 05 和 13。

`oracle` 用真值走同一套控制器。它用来证明「这张桌子和这个控制器是能做完的」。

`SelectActionAdapter` 在 `packages/policies/loopbench_policies/bridge.py`。外面的对象如果有 `select_action` 并且返回张量，适配器把它收成 NumPy。接到参考桌面或 MuJoCo 时，动作被收成 4 维。它不读 `privileged`。

## 四个你会被问到的名字

这些模型都是「看图像、读指令、输出动作」。业内把这类模型叫 VLA（vision-language-action）。你不需要在这一章把网络结构推一遍。需要知道的是调用形状和权重在哪。

| 名字 | 仓库 | 本仓库里的调用 | 权重环境变量 |
| --- | --- | --- | --- |
| ACT | [LeRobot](https://github.com/huggingface/lerobot) 里的 `ACTPolicy` | `from_pretrained` 然后 `select_action` | `LOOPBENCH_ACT_CHECKPOINT` |
| OpenVLA | [openvla/openvla](https://github.com/openvla/openvla) | `AutoModelForVision2Seq.from_pretrained(..., trust_remote_code=True)`，`predict_action` | `LOOPBENCH_OPENVLA_CHECKPOINT` |
| GR00T | [NVIDIA/Isaac-GR00T](https://github.com/NVIDIA/Isaac-GR00T) | `Gr00tPolicy.get_action` | `LOOPBENCH_GR00T_CHECKPOINT` |
| π0 | [Physical-Intelligence/openpi](https://github.com/Physical-Intelligence/openpi) | `get_config("pi0_droid")`，`infer(example)["actions"]` | `LOOPBENCH_PI0_CHECKPOINT` |
| π0.5 | 同一个 openpi 仓库里的另一个配置 | `get_config("pi05_droid")`。LIBERO 微调是另一份 config `pi05_libero` | `LOOPBENCH_PI05_CHECKPOINT` |

π0 和 π0.5 是两个插件、两份检查点。不要合成一个开关。

ACT 一次预测未来一段动作，叫 action chunk。openpi 的 `infer` 也返回多行。接到真实环境时，这些行按时间一步一步交出去，不在协议层砍成 4 个数。4 维只属于参考桌面和 MuJoCo 的适配。

插件报告「可运行」要同时满足两件：库能 import，并且对应的环境变量指向检查点。缺任何一件，`detail` 会写缺的是哪件，API 返回 409。

## 为什么权重不进这个 git 仓库

一份 VLA 检查点是几个 GiB 到几十 GiB，并且许可证和 CUDA、JAX、PyTorch 版本绑在一起。把它们提交进评测仓库，等于把交叉工具链和芯片 ROM 提交进应用仓库。

评测进程只应该依赖 `select_action`。训练依赖留在策略进程里。`loopbench policy-serve` 就是这个进程。评测侧连 `host:port`。

LeRobot 的接入说明：<https://huggingface.co/docs/lerobot/bring_your_own_policies>。

## 读代码的顺序

1. `vision.py` 的 `select_action`。看颜色阈值和它如何拒绝 `privileged`。
2. `oracle.py` 的前 40 行。看它在没有 `privileged` 时直接抛错。
3. `bridge.py` 的 `SelectActionAdapter`。
4. `packages/bridges/loopbench_bridges/policies.py` 里挑一个，建议 `Pi0` 或 `Act`。看 `probe()` 怎样同时检查库和检查点，以及动作块怎样排队。

## 这一章不要求你做的事

不要求下载权重，不要求讲 transformer 的注意力公式。要求你能说明：`vision_v1` 是会失败的伺服，用来把归因跑通；ACT 和 π0 是另一类策略，本仓库只保留官方调用，检查点用环境变量指过去。
