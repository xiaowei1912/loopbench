"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ErrorBlock, LoadingBlock } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api";
import type { Catalog, Job } from "@/lib/types";

export default function EvaluatePage() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [suite, setSuite] = useState("tabletop_probe");
  const [policy, setPolicy] = useState("vision_v1");
  const [simulator, setSimulator] = useState("reference");
  const [episodes, setEpisodes] = useState(1);
  const [seed, setSeed] = useState(0);
  const [frames, setFrames] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const [busy, setBusy] = useState(false);

  function load() {
    setError(null);
    setCatalog(null);
    api<Catalog>("/api/catalog")
      .then(setCatalog)
      .catch((exc: Error) => setError(exc.message));
  }

  useEffect(() => {
    load();
  }, []);

  const selectedSuite = catalog?.suites.find((item) => item.name === suite);
  const selectedPolicy = catalog?.policies.find((item) => item.name === policy);
  const selectedSim = catalog?.simulators.find((item) => item.name === simulator);
  const blocked = selectedPolicy?.available === false || selectedSim?.available === false;
  const episodeCount = (selectedSuite?.tasks.length ?? 0) * (selectedSuite?.cells.length ?? 0) * episodes;

  const warning = useMemo(() => {
    if (episodeCount > 24) return "这一档格子较多。演示用 Probe 或 Smoke，几十秒内能出结论。";
    return null;
  }, [episodeCount]);

  async function start(kind: "eval" | "loop") {
    setBusy(true);
    setJob({ id: "", status: "queued", progress: 0, message: "提交任务" });
    try {
      const created = await api<{ id: string }>("/api/jobs", {
        method: "POST",
        body: JSON.stringify({
          kind,
          suite,
          policy,
          simulator,
          episodes_per_cell: episodes,
          seed,
          capture_frames: frames,
        }),
      });
      for (;;) {
        const next = await api<Job>(`/api/jobs/${created.id}`);
        setJob(next);
        if (next.status === "succeeded" || next.status === "failed") break;
        await new Promise((resolve) => setTimeout(resolve, 400));
      }
    } catch (exc) {
      setJob({
        id: "",
        status: "failed",
        progress: 1,
        message: exc instanceof Error ? exc.message : "任务失败",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-3xl">
      <p className="font-mono text-[11px] tracking-[0.18em] text-oxide">EVALUATE</p>
      <h1 className="font-display mt-2 text-4xl">跑一轮</h1>
      <p className="mt-3 text-sm leading-6 text-muted-foreground">
        只评测会留下一条记录。闭环会先评、再归因、调用策略自己的 improve()，然后用同一套基准再评一次。
      </p>

      {error ? <div className="mt-6"><ErrorBlock detail={error} onRetry={load} /></div> : null}
      {!catalog && !error ? <div className="mt-6"><LoadingBlock label="正在读取已安装的套件" /></div> : null}

      {catalog ? (
        <form
          className="mt-8 grid gap-5"
          onSubmit={(event) => {
            event.preventDefault();
          }}
        >
          <div className="grid gap-4 md:grid-cols-3">
            <Field label="基准">
              <Select value={suite} onValueChange={(value) => value && setSuite(value)}>
                <SelectTrigger className="w-full">
                  <SelectValue>{catalog.suites.find((item) => item.name === suite)?.label ?? suite}</SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {catalog.suites.map((item) => (
                    <SelectItem key={item.name} value={item.name}>
                      {item.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field label="策略">
              <Select value={policy} onValueChange={(value) => value && setPolicy(value)}>
                <SelectTrigger className="w-full">
                  <SelectValue>{policy}</SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {catalog.policies.map((item) => (
                    <SelectItem key={item.name} value={item.name}>
                      {item.available ? item.name : `${item.name} · 未安装`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field label="仿真">
              <Select value={simulator} onValueChange={(value) => value && setSimulator(value)}>
                <SelectTrigger className="w-full">
                  <SelectValue>{simulator}</SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {catalog.simulators.map((item) => (
                    <SelectItem key={item.name} value={item.name}>
                      {item.available ? item.name : `${item.name} · 未安装`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          </div>

          {selectedSuite ? <p className="text-sm leading-6 text-muted-foreground">{selectedSuite.description}</p> : null}
          {selectedSim ? <p className="text-sm leading-6 text-muted-foreground">{selectedSim.detail}</p> : null}
          {selectedPolicy ? (
            <p className="text-sm leading-6 text-muted-foreground">
              {selectedPolicy.detail}
              {selectedPolicy.needs_privileged ? " 评测器会交出真值，这条记录是上界。" : " 评测时不读 privileged。"}
            </p>
          ) : null}
          {blocked ? (
            <p className="text-sm leading-6 text-muted-foreground">这个组合还不能提交。先装上对应的库和权重，目录里的状态会变成可运行。</p>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="每格 episode">
              <Input
                type="number"
                min={1}
                max={8}
                value={episodes}
                onChange={(event) => setEpisodes(Math.max(1, Number(event.target.value) || 1))}
              />
            </Field>
            <Field label="种子">
              <Input type="number" value={seed} onChange={(event) => setSeed(Number(event.target.value) || 0)} />
            </Field>
          </div>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={frames}
              onChange={(event) => setFrames(event.target.checked)}
              className="size-4 accent-[var(--oxide)]"
            />
            保存关键帧（160px PNG，格子多的时候文件会变大）
          </label>

          <p className="font-mono text-xs text-muted-foreground">
            单轮 {episodeCount} 条{warning ? ` · ${warning}` : ""}
          </p>

          <div className="flex flex-col gap-3 sm:flex-row">
            <Button type="button" disabled={busy || blocked} onClick={() => start("loop")} className="h-10 px-4">
              跑闭环
            </Button>
            <Button type="button" variant="outline" disabled={busy || blocked} onClick={() => start("eval")} className="h-10 px-4">
              只评测
            </Button>
          </div>
        </form>
      ) : null}

      {job ? (
        <section className="mt-8 border-t border-border pt-6">
          <div className="flex items-center justify-between gap-3 text-sm">
            <span>{job.message || "排队"}</span>
            <span className="font-mono text-xs text-muted-foreground">{Math.round((job.progress || 0) * 100)}%</span>
          </div>
          <Progress value={Math.round((job.progress || 0) * 100)} className="mt-3" />
          {job.status === "failed" ? (
            <div className="mt-4">
              <ErrorBlock title="这一轮没有跑完" detail={job.message} />
            </div>
          ) : null}
          {job.status === "succeeded" && job.loop_id ? (
            <Link href={`/loops/${job.loop_id}`} className="mt-4 inline-block text-sm text-oxide underline underline-offset-4">
              打开闭环记录
            </Link>
          ) : null}
          {job.status === "succeeded" && job.run_id && !job.loop_id ? (
            <Link href={`/runs/${job.run_id}`} className="mt-4 inline-block text-sm text-oxide underline underline-offset-4">
              打开评测记录
            </Link>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1.5">
      <Label>{label}</Label>
      {children}
    </div>
  );
}
