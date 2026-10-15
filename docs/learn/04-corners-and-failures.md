# 04 工况和失败

嵌入式测试里，你不会把「高温」和「低压」写进同一条结论，然后说是高温导致了失败。机器人评测里同样的错误很常见：又暗、相机又偏，最后把两件事都算进光照。

## 因素是测试项的名字

`Factors` 的字段：

| 字段 | 名义值 | 其它值 | 在参考仿真里大概是什么 |
| --- | --- | --- | --- |
| `clutter` | 0 | 1、2 | 桌面上多几根柱子，挡在直线上 |
| `friction` | `nominal` | `low`、`high` | 低摩擦时搬得太快会滑、会掉 |
| `lighting` | `nominal` | `dim`、`glare` | 变暗或往白里洗 |
| `jitter` | `low` | `high` | 物体出生位置的随机更大 |
| `camera` | `nominal` | `shifted` | 相机平移 `(0.06, -0.045)` 米 |

基准只写这些名字。`CAMERA_SHIFT` 这个元组属于 `loopbench-sim-reference`。换一个仿真时，`camera=shifted` 可以是另一套外参，套件文件不用改。这和「测试项 ID 稳定、寄存器配置属于板级支持包」是同一分工。

一格如果只改了一个字段，叫单因素格。`tabletop_v1` 里还有两格同时改了两个因素，那些格子会跑、会进记录，不进入归因的 delta。规则在 [ADR 0004](../adr/0004-one-factor.md)。

## 失败模式从计数来

`classify` 在 `packages/evalkit/loopbench_evalkit/analysis.py`。它不调用第二个模型。优先级是：

1. 有滑落 → `slip`
2. 抓错过、且从未抓住目标 → `wrong_object`
3. 碰撞次数不少于 8，且从未抓住目标 → `collision`
4. 这个任务需要抓，却从没抓住 → `grasp_miss`
5. 抓住过但没成功 → `placement_error`
6. 推动任务：碰撞多则是碰撞，否则是 `push_miss`
7. 其余 → `timeout`

成功的 episode 没有失败模式。

标签还会再标一层，方便人读：光照或相机加上抓空，标 `perception`；杂乱加上碰撞，标 `geometry`；低摩擦加上滑落，标 `contact`。

## 探针上已经测过的数字

`tabletop_probe`，策略从 `vision_v1` 改进到 `vision_v2`，仿真 `reference`，种子 0，每格 1 条。两任务是 `pick_place` 和 `stack`，六格，一共 12 条。

改进前成功率 0.25（3/12）。改进后 0.9167（11/12）。找回 8 条，退步 0。

| 单因素 | 改进前 | 改进后 |
| --- | --- | --- |
| nominal | 100% | 100% |
| lighting=glare | 0% | 100% |
| lighting=dim | 0% | 100% |
| camera=shifted | 0% | 100% |
| clutter=2 | 0% | 50% |
| friction=low | 50% | 100% |

每格只有 1 条时，百分比很粗。界面保留条数 `n`，读的时候要连 `n` 一起看。

`clutter=2` 的 50% 要拆开：`pick_place` 绕开了柱子，`stack` 仍然撞上。绿色积木挡住黄块之后，侧向路点还会擦到柱子。这是还没补上的几何缺口。文档和界面按这个结果写，不要把它说成杂乱已经修好。

## 归因在比较什么

`analyze` 先算全名义格子的成功率，再对每个单因素格算成功率，delta 是两者之差。下降超过阈值时，生成一条中文说明。相机平移对应说明 id `hand_eye`，暗光和眩光对应颜色，柱子对应净空，低摩擦对应搬运。

高抖动如果没有掉点，说明会记成闭环视觉对抖动是稳的。没有掉点也是一条结果。

## 和你写测试报告的方式对齐

一条好的结论长这样：「`camera=shifted` 这一格，两个任务都抓空，名义格是成功的，所以下一轮先做手眼，而不是先改夹爪力度。」

一条差的结论长这样：「成功率 25%，模型不行。」它没有因素，没有失败模式，下一轮不知道改感知、改路径还是改接触。

## 做完再往下

跑一次探针闭环，留到 13 再拆。现在先读 05，弄清改进那一轮为什么允许看真值。

```bash
loopbench loop --suite tabletop_probe --policy vision_v1 --simulator reference --episodes 1 --seed 0
```

跑完对照上表。名义格不应该退步。`clutter=2` 不应该变成 100%。
