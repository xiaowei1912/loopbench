"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { ErrorBlock, LoadingBlock } from "@/components/states";
import { api } from "@/lib/api";
import { failureLabel, pct, signedPct } from "@/lib/format";
import type { LoopDoc } from "@/lib/types";

export default function LoopPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [loop, setLoop] = useState<LoopDoc | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api<LoopDoc>(`/api/loops/${id}`)
      .then(setLoop)
      .catch((exc: Error) => setError(exc.message));
  }, [id]);

  if (error) return <ErrorBlock detail={error} />;
  if (!loop) return <LoadingBlock label="正在打开闭环" />;

  const comparison = loop.comparison;

  return (
    <div className="max-w-3xl">
      <Link href="/runs" className="font-mono text-[11px] tracking-[0.18em] text-oxide">
        CLOSED LOOP
      </Link>
      <h1 className="font-display mt-2 text-4xl">{loop.suite}</h1>
      <p className="mt-2 font-mono text-xs text-muted-foreground">
        {loop.id} · {loop.policy ?? "policy"} · {loop.simulator} · seed {loop.seed ?? 0}
      </p>

      <div className="mt-6 flex flex-wrap items-end gap-8 border-y border-border py-4">
        <div>
          <div className="font-mono text-[11px] text-muted-foreground">改进前</div>
          <div className="font-display text-4xl tabular-nums">{pct(comparison.before_success_rate)}</div>
        </div>
        <div className="pb-2 text-oxide">→</div>
        <div>
          <div className="font-mono text-[11px] text-muted-foreground">改进后</div>
          <div className="font-display text-4xl tabular-nums">{pct(comparison.after_success_rate)}</div>
        </div>
        <div className="pb-1 text-sm text-muted-foreground">
          {signedPct(comparison.delta)} · 找回 {comparison.recovered} · 退步 {comparison.regressed}
        </div>
      </div>

      <div className="mt-4 flex gap-4 text-sm">
        <Link href={`/runs/${loop.before_id}`} className="text-oxide underline underline-offset-4">
          改进前的记录
        </Link>
        <Link href={`/runs/${loop.after_id}`} className="text-oxide underline underline-offset-4">
          改进后的记录
        </Link>
      </div>

      <section className="mt-8">
        <h2 className="font-display text-2xl">同一格，前后各一次</h2>
        <ul className="mt-4 space-y-3">
          {comparison.slices.map((slice) => (
            <li key={slice.label}>
              <div className="flex justify-between font-mono text-xs">
                <span>{slice.label}</span>
                <span>
                  {pct(slice.before)} → {pct(slice.after)} · {signedPct(slice.delta)}
                </span>
              </div>
              <div className="mt-1 grid grid-cols-2 gap-1">
                <div className="h-1.5 bg-muted">
                  <div className="h-full bg-muted-foreground/50" style={{ width: `${Math.round(slice.before * 100)}%` }} />
                </div>
                <div className="h-1.5 bg-muted">
                  <div className="h-full bg-oxide" style={{ width: `${Math.round(slice.after * 100)}%` }} />
                </div>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {loop.improve?.notes && loop.improve.notes.length > 0 ? (
        <section className="mt-8">
          <h2 className="font-display text-2xl">策略改了什么</h2>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm leading-6">
            {loop.improve.notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
          {loop.improve.levers && loop.improve.levers.length > 0 ? (
            <p className="mt-2 font-mono text-xs text-muted-foreground">
              levers: {loop.improve.levers.filter(Boolean).join(", ")}
            </p>
          ) : null}
        </section>
      ) : null}

      {loop.analysis && loop.analysis.insights.length > 0 ? (
        <section className="mt-8">
          <h2 className="font-display text-2xl">改进前的归因</h2>
          <div className="mt-4 grid gap-4">
            {loop.analysis.insights.map((insight) => (
              <article key={insight.id} className="border-l-2 border-oxide pl-4">
                <h3 className="font-medium">{insight.title}</h3>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">{insight.body}</p>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <section className="mt-8">
        <h2 className="font-display text-2xl">逐条对照</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[32rem] text-left text-sm">
            <thead className="font-mono text-[11px] text-muted-foreground">
              <tr className="border-b border-border">
                <th className="py-2 font-normal">任务</th>
                <th className="py-2 font-normal">因素</th>
                <th className="py-2 font-normal">前</th>
                <th className="py-2 font-normal">后</th>
              </tr>
            </thead>
            <tbody>
              {comparison.pairs.map((pair) => (
                <tr key={`${pair.task}-${pair.factor_label}-${pair.seed}`} className="border-b border-border/70">
                  <td className="py-2">{pair.task_label}</td>
                  <td className="py-2 font-mono text-xs">{pair.factor_label}</td>
                  <td className="py-2">{pair.before ? "成功" : failureLabel(pair.before_failure)}</td>
                  <td className="py-2">{pair.after ? "成功" : failureLabel(pair.after_failure)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
