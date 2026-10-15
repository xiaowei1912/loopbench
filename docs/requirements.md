# 需求

## 用户

做机器人策略的工程师。他拿到一个新仓库或一篇新论文，需要在同一套基准上回答三件事：名义工况过不过、哪一个场景因素让它塌、下一轮该补数据还是该改控制器。

## 必须做到

1. 一条命令或界面上的一次提交，跑完评测或整圈闭环。
2. 基准、仿真、策略可以来自不同的安装包。评测器不 import 它们的模块。
3. 场景因素是名字，不是米或颜色。`camera=shifted` 在参考仿真里是固定平移，在 Isaac 里可以是另一套外参。suite 不写死单位。
4. 失败按 episode trace 分类：抓空、抓错、滑落、碰撞、放置偏差、推动未入区、超时。
5. 归因只用单因素切片，对照全名义工况。交互格可以存在，但不进入那条 delta。
6. 改进阶段可以看真值来做标定。再评测时，如果策略没有声明 `needs_privileged`，真值不得进入 `info`。
7. 参考仿真在 CPU 上确定，同一种子得到同一像素。CI 不申请 GPU。
8. 结果落盘，界面能看成功率、切片、失败说明、关键帧和闭环前后对照。
9. 空记录、API 连不上、任务失败，界面都要说人话，并给出下一步。
10. 一次企业评测是一份实验：场景、本体、任务分开，仿真器声明自己能编译哪一对，策略可以在另一个进程，结果带协议号。不可运行的仿真在任务开始前拒绝。

## 任务词汇

这些 id 是 suite 和仿真之间的合同。仿真可以不实现某一个，但名字不能私自换。

| id | 对应的公开基准 |
| --- | --- |
| pick_place | ManiSkill PickCube，LIBERO object |
| stack | ManiSkill StackCube |
| push | LeRobot PushT |
| drawer | RoboCasa |
| sort | LIBERO-Object |

## 因素

`clutter`、`friction`（low / nominal / high）、`lighting`（dim / nominal / glare）、`jitter`（low / high）、`camera`（nominal / shifted）。

## 套件

| 名字 | 用途 |
| --- | --- |
| tabletop_probe | 抓取放置和叠放，六个单因素格。测试和一键演示。 |
| tabletop_mini | 五任务的单因素扫描。 |
| tabletop_v1 | Mini 再加上 glare×camera、clutter×friction。交互格不参与单因素 delta。 |
| tabletop_smoke | 示例包。只有抓取放置，名义和相机平移。 |

## 非目标

- 替代 Isaac Lab 或 MuJoCo 的物理。
- 复现某篇论文的成功率数字。
- 在这个仓库里下载策略权重。
