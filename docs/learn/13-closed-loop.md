# 13 闭环拆开

闭环的代码在 `packages/evalkit/loopbench_evalkit/loop.py` 的 `run_closed_loop`。界面上一次「闭环」提交走的就是它。

## 五个阶段

1. **评测。** 用 `plugin.make()` 得到 `vision_v1`，在套件上跑完。内部 id 先记成 `before`。
2. **归因。** `analyze(before)` 产生单因素切片、失败计数、中文说明、建议的杠杆。
3. **生成场景。** `generate_scenarios` 最多 24 条，三种策略：
   - `stress`：在已经塌的格子上换一颗种子，用来复现
   - `counterfactual`：同一颗种子，把那个因素拨回名义，用来核对是不是它
   - `calibration`：光照扫描，当作带标签的采集，不计入得分
4. **改进。** `plugin.improve(policy, report, backend.make)`。视觉策略在这里采集颜色并返回 `vision_v2`。笔记写进 `improve.notes`。
5. **再评测。** 同一套件、同一颗种子、新策略。内部 id 记成 `after`。

落盘时 `before` 和 `after` 这两个字不会当作 run id。两次闭环如果都用这两个名字，会互相覆盖。`store.save_run` 把它们换成 `run-` 加随机后缀。

比较按 `(task, factors, seed)` 对齐。上一轮失败、这一轮成功，计为找回。上一轮成功、这一轮失败，计为退步。名义格退步是严重问题：改进把本来能过的工况改坏了。

## 探针数字怎么讲

种子 0，`tabletop_probe`，每格 1 条，参考仿真。

改进前 3/12。名义两任务成功。低摩擦这一格是 50%，两个任务里有一个成功。光照、相机、杂乱失败。低摩擦下的失败模式是滑落：物体不会因为滑进箱子而被算成成功。

改进后 11/12。光照靠冻住的颜色原型。相机靠地标解出平移。低摩擦靠把搬运步长降下来。杂乱下抓取放置绕开柱子，叠放仍然碰撞，所以是 50%，整表是 11/12。

讲的时候带上这些限定：

- 这是脚本策略的杠杆，不是一次神经网络训练。
- 每格 1 条，不能当成大规模统计。
- 叠放加两根柱子仍然失败。
- 同一种子再跑，参考仿真的像素应该一致。

## 一条 run.json 里先看哪几个字段

| 字段 | 含义 |
| --- | --- |
| `suite`、`policy`、`simulator`、`seed` | 这次测试的身份。对比两次运行时先看这四项是否相同 |
| `privileged` | 这次有没有开调试口 |
| `summary.n`、`summary.success`、`summary.success_rate` | 总表 |
| `summary.by_task` | 按任务拆 |
| `summary.by_failure` | 按失败模式拆 |
| `episodes[].factors` | 这一条改了什么 |
| `episodes[].failure` | `grasp_miss` 这一类英文 id |
| `episodes[].metrics` | 步数、路程、碰撞、滑落、抓取次数、目标误差 |
| `analysis.slices` | 单因素 delta。闭环的改进前记录里有 |
| `analysis.insights` | 给人读的说明，例如 `hand_eye` |
| `scenarios` | 下一轮建议加的场景 |

关键帧只在 `capture_frames` 为真时有，PNG 用 base64 放在 `keyframes` 里。默认关掉，避免记录太大。

## 生成的场景没有自动再跑

`generate_scenarios` 的结果写进记录，供人和下一轮实验使用。闭环本身的第二轮用的是同一套件、同一种子，不是这些新场景。新场景是「建议的下一批测试向量」，像测试报告末尾的待补用例。真的要跑它们，要另开一次评测或写进实验 YAML。

## 读代码的顺序

1. `loop.py` 的 `run_closed_loop` 和 `compare_runs`。
2. `analysis.py` 的 `classify` 和 `_one_factor_slices`。
3. `scenarios.py` 的前 40 行。
4. `improve.py` 的 `improve_vision`。

读完应该能指出：第二轮的种子从哪来，退步从哪两个布尔值算出来，叠放撞柱子为什么不会被文档写成已修复。
