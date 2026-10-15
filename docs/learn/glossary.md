# 术语

搜索代码时用左列的英文。

| 英文 | 在本仓库里的意思 |
| --- | --- |
| action | 策略输出的一组数。参考桌面至少 4 维：平面增量、高度、夹爪 |
| action chunk | 一次预测出的未来若干步动作。ACT 和 π0 会这样返回。评测时一步交一行 |
| adapter | 调用了上游官方构造函数，但本机没有那个库或权重。API 会拒绝开跑 |
| benchmark / suite | 一组任务和因素格子。`tabletop_probe` 是一套，LIBERO 也是一套 |
| cell | 基准里的一格，一组 `Factors` |
| checkpoint | 训练好的权重文件。用 `LOOPBENCH_*_CHECKPOINT` 指向它，不提交进 git |
| episode | 一次重置之后的控制循环，直到成功或步数用尽 |
| entry point | setuptools 的插件登记。安装包之后注册表才能按名字找到它 |
| factor | 场景因素的名字，例如 `camera=shifted`。米和颜色不属于因素 |
| Gymnasium | 环境的 `reset` / `step` 约定。本仓库两张桌面和多数上游仿真都遵循它 |
| handler | 一个仿真插件。评测器只看见 `make` 和可选的 `accepts` |
| horizon | 步数上限。参考仿真是 120。用尽则 `truncated` |
| insight | 给人读的归因说明，例如 `hand_eye` |
| observation | 策略能看见的东西。图像、本体状态、任务句子 |
| oracle | 读真值的上界策略。用来证明基准能被做完 |
| policy | 把观测变成动作的对象 |
| privileged | 仿真器内存里的真值。默认不进入 `info` |
| protocol | 实验结果的版本号，当前是 `loopbench.experiment/1` |
| reward | `step` 返回的标量。本仓库分类看 trace，不靠把奖励训练进去 |
| seed | 随机种子。参考仿真上同一种子得到同一像素 |
| success rate | `success / n`。读的时候保留 `n` |
| terminated | 任务完成而结束 |
| truncated | 步数用尽而结束，任务未必完成 |
| trace | 一条 episode 的计数：步数、碰撞、滑落、是否抓住过目标、目标误差 |
| VLA | vision-language-action。图像和语言进去，动作出来的模型 |

失败模式的英文 id：

| id | 中文 |
| --- | --- |
| `grasp_miss` | 抓空 |
| `wrong_object` | 抓错物体 |
| `slip` | 滑落 |
| `collision` | 碰撞卡住 |
| `placement_error` | 放置偏差 |
| `push_miss` | 推动未入区 |
| `timeout` | 超时 |
