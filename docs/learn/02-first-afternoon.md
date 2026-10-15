# 02 第一天下午

目标：在没有 GPU 的机器上跑通两条评测，并在界面上点开结果。预计一小时，含安装。

需要 Python 3.11+ 和 Node 22。MuJoCo 的离屏渲染需要系统库 `libosmesa6`。CI 里会装它；本机没有的话，参考桌面仍然能跑，MuJoCo 的渲染会失败。

## 安装

在仓库根目录：

```bash
make install
export PATH="$HOME/.local/bin:$PATH"
loopbench catalog
```

`catalog` 打印已安装的仿真、策略、基准。你应该能看到仿真名 `reference` 和 `mujoco`，策略名 `oracle` 和 `vision_v1`，基准名里有 `tabletop_smoke` 和 `tabletop_probe`。

`isaac-lab`、`act`、`pi0` 这类名字也会出现在 HTTP 目录里，状态是适配器、当前不可运行。第一天不用管它们。

命令如果不在 `PATH` 上，用：

```bash
python3 -m loopbench_cli.main catalog
```

## 第一条：上界必须能做完

```bash
loopbench eval --suite tabletop_smoke --policy oracle --simulator reference --seed 0
```

`tabletop_smoke` 只有一个任务 `pick_place`，两格：全名义，以及 `camera=shifted`。`oracle` 读真值，两格都应该成功。终端里的 `success_rate` 是 `1.0`。

如果这里失败，先别看视觉策略。环境或特权信息有问题。运行手册里的调试顺序写在 [runbook](../runbook.md)。

## 第二条：量产策略会在一个 corner 上失败

```bash
loopbench eval --suite tabletop_smoke --policy vision_v1 --simulator reference --seed 0
```

名义那一格应该成功。相机平移那一格应该失败，失败模式是抓空。这是设计好的，不是安装坏了。原因在 04 和 05：视觉把像素当成没偏过的相机，抓取门限大约 0.034 米，平移是 `(0.06, -0.045)` 米，手伸到了积木旁边。

## 界面

两个终端：

```bash
loopbench serve --host 0.0.0.0 --port 43124
```

```bash
cd apps/web
npm install
npm run dev
```

打开 <http://127.0.0.1:43123>。

建议点的顺序：

1. **工作台**。首页的 25% 和 92% 是已经测过的探针数字，不是你刚跑的那条。
2. **评测**。套件选 Probe 或 Smoke，策略选 `vision_v1`，仿真选 `reference`。Smoke 更快。
3. **记录**。点进一条 run，看成功率和失败模式。
4. **后端**。分清「可运行」和「适配器已接入」。
5. **架构**。五个平面。入门阶段知道有这页即可，14 再细读。

API 不通时，侧栏会写「API 未连接」。先看 `http://127.0.0.1:43124/api/health` 是否返回 `{"ok": true}`。

## 数据落在哪

默认目录是 `./data`，可以用环境变量 `LOOPBENCH_DATA` 改。一条评测是 `runs/<id>/run.json`。这就是测试报告，和你在 CI 里存的 JUnit XML 同一类东西，只是字段按 episode 组织。

`.gitignore` 忽略了 `data/`。不要把本机跑出来的记录提交进 git。

## 先不要跑的命令

`loopbench loop --suite tabletop_probe` 会评两轮，CPU 上大约几十秒，适合 04 之后再跑。Mini 和 v1 格子更多。Isaac、GR00T 在这台机器上不会真的步进。

## 做完再往下

你手头有一次 `oracle` 的全成功，和一次 `vision_v1` 的部分失败。下一章把其中一条 episode 按时间拆开。
