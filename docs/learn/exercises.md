# 练习

七个练习都不需要 GPU。做完再看文末的对照。命令都在仓库根目录，并且已经 `make install`。

## 1. 目录里谁能跑

运行 `loopbench catalog`，或请求 `GET /api/catalog`。

写下两件：

- 两个 `support` 为可运行的仿真名字
- 一个你认为不该在这台机器上开跑的仿真名字，以及 API 会用什么状态码拒绝它

## 2. 上界

```bash
loopbench eval --suite tabletop_smoke --policy oracle --simulator reference --seed 0
```

记录 `summary.success_rate` 和 `summary.n`。

## 3. 一个故意的失败

把策略换成 `vision_v1`，套件和种子不变。

回答：哪一格失败，失败模式的英文 id 是什么，它属于感知、几何还是接触。

## 4. 在代码里指出闸门

打开 `packages/evalkit/loopbench_evalkit/runner.py`。

指出创建环境时谁决定 `expose_privileged`。再打开 `analysis.py` 的 `classify`，按顺序列出前三个失败模式。

## 5. 数在哪个包

`camera=shifted` 的平移量是多少，写在哪个文件的哪个常量里。套件文件 `suites.py` 里有没有这个米制。

## 6. 包边界

运行 `python3 scripts/check_boundaries.py`。

如果在 `packages/evalkit` 里增加一行 `import loopbench_sim_reference`，这个脚本会怎样。不要把这行留在工作区里。

## 7. 读一条记录

跑完练习 3 之后，如果开着 API，记录在 `LOOPBENCH_DATA` 或 `./data/runs/`。打开一份 `run.json`。

找出一条失败 episode 的 `factors`、`failure`、`metrics.grasp_attempts`。说明 `privileged` 这个运行级字段为什么是假。

## 对照

1. 可运行的仿真是 `reference` 和 `mujoco`。`isaac-lab` 或其它适配器提交任务时返回 409。
2. `n` 是 2，`success_rate` 是 1。两格都成功。
3. `camera=shifted` 失败，模式是 `grasp_miss`，标签是 `perception`。名义格成功。
4. `expose_privileged` 来自 `policy.needs_privileged`。`classify` 的前三个是 `slip`、`wrong_object`、`collision`。
5. `CAMERA_SHIFT = (0.06, -0.045)`，在 `packages/sim-reference/loopbench_sim_reference/constants.py`。`suites.py` 只写 `Factors(camera="shifted")`，没有米。
6. 脚本打印那一行 import 并返回非零。CI 的 `python` job 会红。
7. 运行级 `privileged` 为假，因为 `vision_v1.needs_privileged` 是 `False`。抓取次数至少为 1 时，说明它尝试过，但没抓到目标，所以模式是抓空而不是超时。
