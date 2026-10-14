import { Button } from "@/components/ui/button";

export function LoadingBlock({ label = "正在读取" }: { label?: string }) {
  return (
    <div className="rounded-lg border border-dashed border-border px-4 py-8 text-sm text-muted-foreground">
      {label}…
    </div>
  );
}

export function ErrorBlock({
  title = "没有拿到数据",
  detail,
  onRetry,
}: {
  title?: string;
  detail: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-4">
      <div className="font-medium text-destructive">{title}</div>
      <p className="mt-1 text-sm text-muted-foreground">{detail}</p>
      {detail.includes("fetch") || detail.includes("Failed") || detail.includes("ECONNREFUSED") ? (
        <p className="mt-2 font-mono text-xs text-muted-foreground">loopbench serve --port 43124</p>
      ) : null}
      {onRetry ? (
        <Button variant="outline" className="mt-3" onClick={onRetry}>
          重试
        </Button>
      ) : null}
    </div>
  );
}

export function EmptyBlock({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="rounded-lg border border-dashed border-border px-4 py-8">
      <div className="font-display text-lg">{title}</div>
      <p className="mt-1 max-w-md text-sm text-muted-foreground">{detail}</p>
    </div>
  );
}
