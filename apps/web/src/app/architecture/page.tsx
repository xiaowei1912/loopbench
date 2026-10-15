"use client";

import { useEffect, useState } from "react";

import { ErrorBlock, LoadingBlock } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import type { Catalog, Platform } from "@/lib/types";

const PLANES = [
  {
    id: "compose",
    title: "组合",
    source: "Isaac Lab-Arena",
    body: "一个环境是场景 × 本体 × 任务。参考桌面和 MuJoCo 只接受 tabletop × planar_gripper。厨房或 Franka 会在开跑之前被拒绝，而不是跑出一条假成功。",
  },
  {
    id: "handler",
    title: "仿真 handler",
    source: "RoboVerse / MetaSim",
    body: "每个仿真器是一个插件。评测器只调用 make() 和可选的 accepts()。Isaac、ManiSkill、LIBERO、RoboCasa、RoboTwin 仍是适配器：库不在这个仓库里。",
  },
  {
    id: "policy",
    title: "策略进程",
    source: "XPolicyLab",
    body: "策略可以留在另一个进程。线上是 TCP 上的一行 JSON：reset、act、close。评测进程不安装那个策略的依赖。oracle 走远程时必须声明 needs_privileged，否则真值不会送过线。",
  },
  {
    id: "experiment",
    title: "实验",
    source: "Isaac Lab-Arena",
    body: "一份 YAML 描述一次实验：shared 给出仿真、种子和每格条数，每个 run 选一个已安装基准或一个组合单元，再选策略。文件在 experiments/tabletop_smoke.yaml。",
  },
  {
    id: "protocol",
    title: "协议",
    source: "vla-evaluation-harness",
    body: "每次实验结果都带协议号。种子、条数、策略、仿真和端点写在同一条记录里。换一个没写下来的参数，成功率可以差出几十个百分点，所以协议是结果的一部分。",
  },
];

const YAML = `name: tabletop_smoke
shared:
  simulator: reference
  seed: 0
  episodes_per_cell: 1
runs:
  - name: oracle
    suite: tabletop_smoke
    policy: oracle
  - name: vision
    suite: tabletop_smoke
    policy: vision_v1`;

export default function ArchitecturePage() {
  const [platform, setPlatform] = useState<Platform | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    setError(null);
    Promise.all([api<Platform>("/api/platform"), api<Catalog>("/api/catalog")])
      .then(([nextPlatform, nextCatalog]) => {
        setPlatform(nextPlatform);
        setCatalog(nextCatalog);
      })
      .catch((exc: Error) => setError(exc.message));
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="max-w-3xl">
      <p className="font-mono text-[11px] tracking-[0.18em] text-oxide">PLATFORM</p>
      <h1 className="font-display mt-2 text-4xl">企业级评测平面</h1>
      <p className="mt-3 text-sm leading-6 text-muted-foreground">
        这些接缝来自公开的评测系统。仓库实现的是合同，不是把上游源码拷进来。OSMO 多机调度、XPolicyLab 的策略目录、vla-eval 的基准镜像都没有打进这个仓库。
      </p>

      {error ? (
        <div className="mt-6">
          <ErrorBlock detail={error} onRetry={load} />
        </div>
      ) : null}
      {!platform && !error ? (
        <div className="mt-6">
          <LoadingBlock />
        </div>
      ) : null}

      {platform ? (
        <div className="mt-8 space-y-10">
          <p className="font-mono text-xs text-muted-foreground">
            protocol <span className="text-foreground">{platform.protocol}</span>
          </p>

          <section>
            <h2 className="font-display text-2xl">五个平面</h2>
            <ol className="mt-4 space-y-4">
              {PLANES.map((plane, index) => (
                <li key={plane.id} className="border border-border bg-card p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-[11px] text-oxide">0{index + 1}</span>
                    <h3 className="font-display text-xl">{plane.title}</h3>
                    <Badge variant="outline">{plane.source}</Badge>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{plane.body}</p>
                </li>
              ))}
            </ol>
          </section>

          <section>
            <h2 className="font-display text-2xl">实验文件</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              命令是 <span className="font-mono text-xs">loopbench experiment experiments/tabletop_smoke.yaml</span>
              。策略单独起进程时用 <span className="font-mono text-xs">loopbench policy-serve --policy oracle --port 43126</span>
              ，run 里写 <span className="font-mono text-xs">endpoint: 127.0.0.1:43126</span>。
            </p>
            <pre className="mt-3 overflow-x-auto border border-border bg-card p-4 font-mono text-xs leading-6">{YAML}</pre>
          </section>

          <section>
            <h2 className="font-display text-2xl">采用了什么</h2>
            <ul className="mt-4 space-y-3">
              {platform.sources.map((source) => (
                <li key={source.id} className="border-b border-border pb-3">
                  <a href={source.url} className="font-mono text-sm text-oxide underline underline-offset-4">
                    {source.id}
                  </a>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">{source.adopted}</p>
                </li>
              ))}
            </ul>
          </section>

          {catalog ? (
            <section>
              <h2 className="font-display text-2xl">现在装上的 handler</h2>
              <ul className="mt-4 space-y-2 text-sm">
                {catalog.simulators.map((item) => (
                  <li key={item.name} className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs">{item.name}</span>
                    <Badge variant="outline">{item.support === "runnable" ? "可运行" : "适配器"}</Badge>
                    <span className="text-muted-foreground">{item.detail}</span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
