# 运行手册

嵌入式或 CI 背景、第一次接触这个仓库时，先读 [学习文档](learning.md)，从第一天下午那一章把 `tabletop_smoke` 跑通。这一页只保留命令和故障位置。

## 本机

```bash
make install
export PATH="$HOME/.local/bin:$PATH"
python3 scripts/check_boundaries.py
python3 -m pytest tests -q
loopbench catalog
loopbench eval --suite tabletop_smoke --policy oracle
loopbench loop --suite tabletop_probe --policy vision_v1 --episodes 1 --seed 0
loopbench serve --host 0.0.0.0 --port 43124
```

另一个终端：

```bash
cd apps/web
npm install
npm run dev
```

打开 <http://127.0.0.1:43123>。Probe 闭环在 CPU 上大约几十秒。Mini 和 v1 格子多，界面会提示。

数据目录默认是 `./data`，可用 `LOOPBENCH_DATA` 改。评测在 `runs/<id>/run.json`，闭环在 `loops/<id>.json`。

## Docker

```bash
docker compose up --build
```

Web 镜像在构建时把 `API_ORIGIN` 写成 `http://api:43124`，因为 Next.js 的 rewrite 在 build 时写进路由。换地址要重新构建 web 镜像。

## 这个 demo 不跑的东西

- 不启动 Isaac Sim，不申请 GPU，不编译 CUDA。
- 不下载 GR00T、openpi、OpenVLA 的权重。
- 不渲染 USD 资产。参考仿真是 160×160 的俯视光栅。

适配器页里的「未安装」是诚实状态。`probe()` 只做 `importlib.import_module`。

## 真的要接 Isaac Lab 时会碰到的问题

这些是那条路上的常见故障，不是这个仓库里的开关。

| 现象 | 通常在哪一层 |
| --- | --- |
| `isaaclab` import 失败 | 容器里的 Isaac Sim 版本和 Isaac Lab 提交没对齐。先在 Isaac 自己的镜像里跑通官方教程，再写 Backend。 |
| Gym id 已注册 | 进程里 `gym.register` 跑了两次。参考仿真的 `register_gym()` 会忽略重复注册。Isaac 侧要用官方入口，不要在 import 时再注册一遍。 |
| 策略动作维度和机器人对不上 | 先在 `select_action` 边界上打印 shape。评测器只要求至少 4 维给参考桌面。真机或 Franka 的动作空间由那个 Env 声明，不要改 suite。 |
| 相机外参漂了，抓取全空 | 这就是参考仿真里 `camera=shifted` 在演示的事。地标或手眼标定放在 `improve()` 或 episode 开始，不要把真值留在部署策略里。 |
| 资产路径在容器里变了 | USD、网格、BDDL 用环境变量或包内相对路径。不要把绝对路径写进 suite。 |
| Docker 里 GPU 看不见 | `--gpus all` 和 NVIDIA container toolkit 是宿主机的事。Loopbench 的 API 镜像是 CPU，不要往它里面塞 Isaac。Isaac 应该是另一个服务，通过策略或仿真插件说话。 |

## 调试顺序

1. `loopbench catalog` 看插件在不在。不在就是没安装，或 entry point 组名写错。
2. 用 `tabletop_smoke` 和 `oracle` 确认环境和特权策略。这两格都应该成功。
3. 换成 `vision_v1`。相机平移这一格应该失败，名义工况应该成功。如果名义也失败，先看感知，不要先看闭环。
4. 再跑 `tabletop_probe` 的闭环。名义工况退步就是改进把好的格子改坏了。
5. 最后才换 Mini 或自己的仿真。

## 测试

`tests/test_packages.py` 锁住：示例套件被发现、oracle 五个名义任务、相机平移下两个任务都抓空、闭环名义不退步且 glare 回来、`SelectActionAdapter`、像素确定。

`tests/test_api.py` 用临时 `LOOPBENCH_DATA`，检查 catalog、oracle 评测，以及闭环落成两个不同的 run id。
