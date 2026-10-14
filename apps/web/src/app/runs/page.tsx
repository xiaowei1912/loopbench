"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { EmptyBlock, ErrorBlock, LoadingBlock } from "@/components/states";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import { pct, signedPct } from "@/lib/format";
import type { LoopRow, RunRow } from "@/lib/types";

export default function RunsPage() {
  const [runs, setRuns] = useState<RunRow[] | null>(null);
  const [loops, setLoops] = useState<LoopRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    setError(null);
    Promise.all([api<{ runs: RunRow[] }>("/api/runs"), api<{ loops: LoopRow[] }>("/api/loops")])
      .then(([runPayload, loopPayload]) => {
        setRuns(runPayload.runs);
        setLoops(loopPayload.loops);
      })
      .catch((exc: Error) => setError(exc.message));
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="max-w-3xl">
      <p className="font-mono text-[11px] tracking-[0.18em] text-oxide">RECORDS</p>
      <h1 className="font-display mt-2 text-4xl">记录</h1>
      <p className="mt-3 text-sm leading-6 text-muted-foreground">评测和闭环都写在本机的 data 目录里。刷新页面之后还在。</p>

      {error ? <div className="mt-6"><ErrorBlock detail={error} onRetry={load} /></div> : null}
      {!runs && !error ? <div className="mt-6"><LoadingBlock /></div> : null}

      {runs && loops ? (
        <Tabs defaultValue="loops" className="mt-8">
          <TabsList>
            <TabsTrigger value="loops">闭环</TabsTrigger>
            <TabsTrigger value="runs">评测</TabsTrigger>
          </TabsList>
          <TabsContent value="loops" className="mt-4">
            {loops.length === 0 ? (
              <EmptyBlock title="还没有闭环" detail="从评测页跑一轮 Probe。改进前后会各留下一条评测记录。" />
            ) : (
              <ul className="divide-y divide-border border-y border-border">
                {loops.map((item) => (
                  <li key={item.id}>
                    <Link href={`/loops/${item.id}`} className="flex items-baseline justify-between gap-4 py-3 hover:bg-muted/60">
                      <span>
                        <span className="font-mono text-xs text-muted-foreground">{item.id}</span>
                        <span className="mt-1 block text-sm">{item.suite}</span>
                      </span>
                      <span className="font-mono text-sm tabular-nums">
                        {pct(item.before_success_rate)} → {pct(item.after_success_rate)}
                        <span className="ml-2 text-muted-foreground">{signedPct(item.delta)}</span>
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </TabsContent>
          <TabsContent value="runs" className="mt-4">
            {runs.length === 0 ? (
              <EmptyBlock title="还没有评测" detail="只评测或闭环都会在这里出现。闭环的改进前、改进后是两条独立记录。" />
            ) : (
              <ul className="divide-y divide-border border-y border-border">
                {runs.map((item) => (
                  <li key={item.id}>
                    <Link href={`/runs/${item.id}`} className="flex items-baseline justify-between gap-4 py-3 hover:bg-muted/60">
                      <span>
                        <span className="font-mono text-xs text-muted-foreground">{item.id}</span>
                        <span className="mt-1 block text-sm">
                          {item.suite ?? "suite"} · {item.policy ?? "policy"}
                          {item.privileged ? " · privileged" : ""}
                        </span>
                      </span>
                      <span className="font-mono text-sm tabular-nums">{pct(item.summary?.success_rate)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </TabsContent>
        </Tabs>
      ) : null}
    </div>
  );
}
