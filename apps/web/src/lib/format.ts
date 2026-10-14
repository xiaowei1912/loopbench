export const FAILURE_LABELS: Record<string, string> = {
  grasp_miss: "抓空",
  wrong_object: "抓错物体",
  slip: "滑落",
  collision: "碰撞卡住",
  placement_error: "放置偏差",
  push_miss: "推动未入区",
  timeout: "超时",
};

export const STRATEGY_LABELS: Record<string, string> = {
  stress: "加压复现",
  counterfactual: "反事实",
  calibration: "标定采集",
};

export function pct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return `${Math.round(value * 100)}%`;
}

export function signedPct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  const points = Math.round(value * 100);
  return `${points > 0 ? "+" : ""}${points}%`;
}

export function failureLabel(mode: string | null | undefined): string {
  if (!mode) return "成功";
  return FAILURE_LABELS[mode] ?? mode;
}
