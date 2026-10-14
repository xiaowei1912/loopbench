"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { ErrorBlock, LoadingBlock } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { failureLabel, pct, signedPct, STRATEGY_LABELS } from "@/lib/format";
import type { Run } from "@/lib/types";

export default function RunPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api<Run>(`/api/runs/${id}`)
      .then(setRun)
      .catch((exc: Error) => setError(exc.message));
  }, [id]);

  if (error) return <ErrorBlock detail={error} />;
  if (!run) return <LoadingBlock label="正在打开记录" />;

  const episodes = run.episodes ?? [];

  return (
    <div className="max-w-3xl">
      <Link href="/runs" className="font-mono text-[11px] tracking-[0.18em] text-oxide">
        RECORDS
      </Link>
      <h1 className="font-display mt-2 text-4xl">{run.suite}</h1>
      <p className="mt-2 font-mono text-xs text-muted-foreground">
        {run.id} · {run.policy} · {run.simulator} · seed {run.seed}
        {run.privileged ? " · privileged" : ""}
      </p>
      {run.privileged ? (
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          这条策略声明了 needs_privileged。评测器交出了真值，它是上界，不是可以部署的视觉策略。
        </p>
      ) : null}

      <div className="mt-6 flex flex-wrap gap-6 border-y border-border py-4">
        <Stat label="成功率" value={pct(run.summary.success_rate)} />
        <Stat label="成功" value={`${run.summary.success}/${run.summary.n}`} />
        <Stat label="每格" value={String(run.episodes_per_cell)} />
      </div>

      {run.analysis ? (
        <section className="mt-8">
          <h2 className="font-display text-2xl">单因素切片</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            名义工况 {pct(run.analysis.baseline_success_rate)}，n={run.analysis.baseline_n}。delta 是相对名义工况，不是相对上一轮。
          </p>
          <ul className="mt-4 space-y-3">
            {run.analysis.slices.map((slice) => (
              <li key={slice.label}>
                <div className="flex justify-between font-mono text-xs">
                  <span>{slice.label}</span>
                  <span>
                    {pct(slice.success_rate)} · {signedPct(slice.delta)} · n={slice.n}
                  </span>
                </div>
                <div className="mt-1 h-1.5 bg-muted">
                  <div className="h-full bg-oxide" style={{ width: `${Math.round(slice.success_rate * 100)}%` }} />
                </div>
              </li>
            ))}
          </ul>
          {run.analysis.slices.length === 0 ? (
            <p className="mt-3 text-sm text-muted-foreground">这一套基准没有单因素格子。</p>
          ) : null}
        </section>
      ) : null}

      {run.analysis && run.analysis.insights.length > 0 ? (
        <section className="mt-8">
          <h2 className="font-display text-2xl">读出来的失败</h2>
          <div className="mt-4 grid gap-4">
            {run.analysis.insights.map((insight) => (
              <article key={insight.id} className="border-l-2 border-oxide pl-4">
                <h3 className="font-medium">{insight.title}</h3>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">{insight.body}</p>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {run.analysis && run.analysis.recommendations.length > 0 ? (
        <section className="mt-8">
          <h2 className="font-display text-2xl">建议的杠杆</h2>
          <ul className="mt-3 space-y-3">
            {run.analysis.recommendations.map((item) => (
              <li key={item.lever}>
                <div className="font-mono text-xs text-oxide">{item.lever}</div>
                <div className="text-sm">{item.title}</div>
                <p className="text-sm leading-6 text-muted-foreground">{item.detail}</p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="mt-8">
        <h2 className="font-display text-2xl">Episode</h2>
        {episodes.length === 0 ? (
          <p className="mt-3 text-sm text-muted-foreground">摘要里没有 episode 明细。</p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[36rem] text-left text-sm">
              <thead className="font-mono text-[11px] text-muted-foreground">
                <tr className="border-b border-border">
                  <th className="py-2 font-normal">任务</th>
                  <th className="py-2 font-normal">因素</th>
                  <th className="py-2 font-normal">结果</th>
                  <th className="py-2 font-normal">步数</th>
                  <th className="py-2 font-normal">碰撞</th>
                </tr>
              </thead>
              <tbody>
                {episodes.map((episode) => (
                  <tr key={`${episode.task}-${episode.factor_label}-${episode.seed}`} className="border-b border-border/70 align-top">
                    <td className="py-2">
                      {episode.task_label}
                      <div className="font-mono text-[11px] text-muted-foreground">{episode.language}</div>
                    </td>
                    <td className="py-2 font-mono text-xs">{episode.factor_label}</td>
                    <td className="py-2">
                      <Badge variant={episode.success ? "secondary" : "destructive"}>
                        {episode.success ? "成功" : failureLabel(episode.failure)}
                      </Badge>
                    </td>
                    <td className="py-2 tabular-nums">{episode.metrics.steps}</td>
                    <td className="py-2 tabular-nums">{episode.metrics.collisions}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {episodes.some((episode) => episode.keyframes.length > 0) ? (
        <section className="mt-8">
          <h2 className="font-display text-2xl">关键帧</h2>
          <div className="mt-4 grid gap-4">
            {episodes
              .filter((episode) => episode.keyframes.length > 0)
              .map((episode) => (
                <div key={`${episode.task}-${episode.seed}-frames`}>
                  <div className="font-mono text-xs text-muted-foreground">
                    {episode.task_label} · {episode.factor_label}
                  </div>
                  <div className="mt-2 flex gap-2 overflow-x-auto">
                    {episode.keyframes.map((frame) => (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        key={frame.step}
                        alt={`${episode.task_label} 第 ${frame.step} 步`}
                        src={`data:image/png;base64,${frame.png}`}
                        className="h-28 w-28 border border-border bg-white object-contain"
                      />
                    ))}
                  </div>
                </div>
              ))}
          </div>
        </section>
      ) : null}

      {run.scenarios && run.scenarios.length > 0 ? (
        <section className="mt-8">
          <h2 className="font-display text-2xl">下一轮场景</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {run.scenarios.slice(0, 12).map((scenario, index) => (
              <li key={`${scenario.strategy}-${scenario.task}-${index}`} className="leading-6">
                <span className="font-mono text-xs text-oxide">{STRATEGY_LABELS[scenario.strategy] ?? scenario.strategy}</span>
                <span className="ml-2">{scenario.reason}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="font-mono text-[11px] text-muted-foreground">{label}</div>
      <div className="font-display text-3xl tabular-nums">{value}</div>
    </div>
  );
}
