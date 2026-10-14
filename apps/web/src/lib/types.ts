export type SuiteInfo = {
  name: string;
  label: string;
  description: string;
  tasks: string[];
  cells: { label: string }[];
  upstream: string;
  upstream_url: string;
};

export type PolicyInfo = {
  name: string;
  available: boolean;
  kind: string;
  support?: string;
  needs_privileged: boolean;
  detail: string;
  upstream?: string;
  upstream_url?: string;
};

export type SimulatorInfo = {
  name: string;
  available: boolean;
  kind: string;
  support?: string;
  detail: string;
  gym_id?: string;
  upstream?: string;
  upstream_url?: string;
};

export type TaskInfo = {
  id: string;
  label: string;
  family: string;
  instruction: string;
  needs_grasp: boolean;
  upstream: string;
  upstream_url: string;
};

export type AdapterInfo = {
  id: string;
  module: string;
  role: string;
  glue: string;
  url: string;
  available: boolean;
  detail: string;
};

export type Catalog = {
  simulators: SimulatorInfo[];
  policies: PolicyInfo[];
  suites: SuiteInfo[];
  tasks: TaskInfo[];
  adapters: AdapterInfo[];
};

export type Job = {
  id: string;
  status: "queued" | "running" | "succeeded" | "failed";
  progress: number;
  message: string;
  kind?: string;
  run_id?: string;
  loop_id?: string;
};

export type Summary = {
  n: number;
  success: number;
  success_rate: number;
  by_task: Record<string, { n: number; success: number; label: string; success_rate: number }>;
  by_failure: Record<string, number>;
};

export type Episode = {
  task: string;
  task_label: string;
  seed: number;
  factor_label: string;
  language: string;
  success: boolean;
  failure: string | null;
  tags: string[];
  metrics: {
    steps: number;
    path_length: number;
    collisions: number;
    slips: number;
    grasp_attempts: number;
    wrong_grasps: number;
    goal_error: number | null;
  };
  keyframes: { step: number; png: string }[];
};

export type Insight = { id: string; title: string; body: string };
export type Slice = {
  factor: string;
  level: string | number;
  n: number;
  success_rate: number;
  delta: number | null;
  label: string;
};
export type Scenario = {
  strategy: string;
  task: string;
  seed: number;
  factors: Record<string, string | number>;
  reason: string;
};
export type Recommendation = { lever: string; title: string; detail: string };

export type Analysis = {
  baseline_success_rate: number;
  baseline_n: number;
  slices: Slice[];
  failures: { mode: string; label: string; count: number }[];
  insights: Insight[];
  recommendations: Recommendation[];
};

export type Run = {
  id: string;
  suite: string;
  policy: string;
  simulator: string;
  seed: number;
  episodes_per_cell: number;
  privileged: boolean;
  summary: Summary;
  episodes?: Episode[];
  analysis?: Analysis;
  scenarios?: Scenario[];
};

export type RunRow = {
  id: string;
  suite?: string;
  policy?: string;
  simulator?: string;
  seed?: number;
  privileged?: boolean;
  summary?: Summary;
  episodes?: number;
};

export type LoopDoc = {
  id: string;
  suite: string;
  simulator: string;
  policy?: string;
  seed?: number;
  episodes_per_cell?: number;
  before_id: string;
  after_id: string;
  before: { id: string; summary: Summary };
  after: { id: string; summary: Summary };
  analysis?: Analysis;
  scenarios?: Scenario[];
  improve?: { notes?: string[]; levers?: (string | null)[]; calibration_scenes?: number };
  comparison: {
    before_success_rate: number;
    after_success_rate: number;
    delta: number;
    recovered: number;
    regressed: number;
    pairs: {
      task: string;
      task_label: string;
      factor_label: string;
      seed: number;
      before: boolean;
      after: boolean;
      before_failure: string | null;
      after_failure: string | null;
    }[];
    slices: { label: string; before: number; after: number; delta: number; n: number }[];
  };
};

export type LoopRow = {
  id: string;
  suite: string;
  simulator: string;
  before_success_rate: number | null;
  after_success_rate: number | null;
  delta: number | null;
  recovered: number | null;
  regressed: number | null;
};
