"use client";

import { Button } from "@/components/ui/button";

export default function ErrorPage({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="max-w-xl">
      <p className="font-mono text-[11px] tracking-[0.18em] text-oxide">ERROR</p>
      <h1 className="font-display mt-2 text-4xl">页面没有渲染完</h1>
      <p className="mt-3 text-sm text-muted-foreground">{error.message}</p>
      <Button className="mt-6" onClick={reset}>
        再试一次
      </Button>
    </div>
  );
}
