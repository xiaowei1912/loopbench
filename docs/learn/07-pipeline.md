# 07 你已经会的流水线

`.github/workflows/ci.yml` 在每次 push 和 pull request 上跑两个 job。它们互不依赖，和一个仓库里「固件交叉编译」与「上位机工具构建」分开跑是同一结构。

## python

1. `actions/checkout`
2. Python 3.12
3. `sudo apt-get install -y libosmesa6`。这是 MuJoCo 离屏渲染要的系统库，相当于测试机上要先有的工具链包。
4. `python -m venv .venv`
5. `make install PIP=.venv/bin/pip BREAK=`。CI 里有虚拟环境，所以不用 `--break-system-packages`。本机没有 venv 模块时，Makefile 默认会加上那个标志。
6. `make test`。先 `scripts/check_boundaries.py`，再 `pytest`。

pytest 守住的行为包括：插件能被发现、第三方套件出现在目录里、oracle 名义工况能做完、相机平移下视觉策略抓空、闭环名义不退步、MuJoCo 抓取放置成功、用假模块检查 Isaac 和几类 VLA 的调用形状、没安装的仿真在任务开始前被拒绝、实验 YAML 和 TCP 上的 oracle。

假模块的意思是：测试进程里放一个同名的 Python 模块，断言适配器调用了官方的 `gym.make` 或 `infer`。CI 不下载 Isaac，也不下载权重。

## web

在 `apps/web` 里 `npm ci`，然后 `npm run build`。它不跑浏览器。构建失败通常是类型或 Next.js 的页面写错，和仿真无关。

界面开发端口是 43123，API 是 43124。选这两个端口是为了躲开 3000、5173、8080。Next 把 `/api` 重写到 API。Docker 构建 web 镜像时，这个地址写成 `http://api:43124`，写在构建参数里，换地址要重新构建。

## 为什么 Isaac 不在这个 job 里

硬件在环的机架不会出现在每一台 GitHub runner 上。你不会让每条固件 PR 都等唯一那块板子。Isaac Sim 同样要 GPU 和一套对齐的版本。

所以门禁分成两层：

- CI 里真的步进的，是参考桌面和 MuJoCo 桌面。
- 没装的仿真，插件 `probe()` 报告 `available: false`、`support: "adapter"`。`POST /api/jobs` 和 `POST /api/experiments` 返回 409，正文说明缺什么。任务不会被标成成功。

这是诚实的红，不是跳过。界面上的徽章是「可运行」「适配器已接入」「未安装」。

## Docker

`docker compose up --build` 起 API 和 web，端口仍是 43124 和 43123。闭环数据在 volume `loopbench-data`。API 镜像同样安装 `libosmesa6`，并设置 `MUJOCO_GL=osmesa`。

不要把 Isaac 塞进这个 CPU 镜像。Isaac 应该是另一个服务。这个仓库的策略传输就是为那种拆分留的口子：评测进程只拿动作。

## 一条失败的 CI 怎么读

| 日志里先看到什么 | 多半是什么 |
| --- | --- |
| `boundaries ok` 之前就退出，并打印某个 `import` | 包越界。评测器 import 了仿真，或策略 import 了评测 |
| pytest 里 MuJoCo 相关失败，提到 GL 或 OSMesa | 系统库没装，或 `MUJOCO_GL` 在库缺失时被设成了 `osmesa` |
| `tabletop_smoke` 的 oracle 不是全成功 | 参考仿真或特权信息坏了。先别看视觉 |
| 相机平移那条测试突然全成功 | 有人把真值漏给了视觉策略，或平移量被改得小于抓取门限 |
| 闭环后退步 | `improve()` 把名义格改坏了 |
| `web` job 失败，`python` 是绿的 | 只看 `apps/web` |

本地复现：

```bash
python3 scripts/check_boundaries.py
MUJOCO_GL=osmesa python3 -m pytest tests -q
```

## 做完再往下

入门到这里可以停。你已经能跑、能读失败、能看 CI。

接下来的章节是深入。下一份工作如果是接仿真，读 10。如果是接一个已有的基准仓库，读 11。如果是接一个带权重的策略，读 12。如果是把探针数字讲给别人听，读 13。
