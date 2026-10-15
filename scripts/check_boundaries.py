"""Package boundaries. Eval does not import a simulator. A policy does not import eval."""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

RULES = {
    "packages/spec": ("loopbench_sim_reference", "loopbench_policies", "loopbench_evalkit", "loopbench_api"),
    "packages/sim-reference": ("loopbench_policies", "loopbench_evalkit", "loopbench_api", "loopbench_adapters"),
    "packages/sim-mujoco": ("loopbench_policies", "loopbench_evalkit", "loopbench_api", "loopbench_adapters", "loopbench_bridges"),
    "packages/policies": ("loopbench_sim_reference", "loopbench_evalkit", "loopbench_api", "loopbench_adapters"),
    "packages/bridges": (
        "loopbench_sim_reference",
        "loopbench_sim_mujoco",
        "loopbench_policies",
        "loopbench_evalkit",
        "loopbench_api",
        "loopbench_adapters",
    ),
    "packages/transport": (
        "loopbench_sim_reference",
        "loopbench_sim_mujoco",
        "loopbench_policies",
        "loopbench_evalkit",
        "loopbench_api",
        "loopbench_adapters",
        "loopbench_bridges",
    ),
    "packages/evalkit": ("loopbench_sim_reference", "loopbench_policies", "loopbench_api", "loopbench_adapters", "loopbench_transport"),
    "packages/adapters": ("loopbench_sim_reference", "loopbench_policies", "loopbench_evalkit", "loopbench_api"),
    "packages/api": ("loopbench_sim_reference", "loopbench_policies"),
    "packages/example-suite": ("loopbench_sim_reference", "loopbench_policies", "loopbench_evalkit", "loopbench_api"),
}


def main() -> int:
    failures = []
    for folder, banned in RULES.items():
        base = ROOT / folder
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for line in text.splitlines():
                code = line.split("#", 1)[0]
                if "import" not in code and "import_module" not in code:
                    continue
                for name in banned:
                    if name in code:
                        failures.append(f"{path.relative_to(ROOT)}: {line.strip()}")
    if failures:
        print("\n".join(failures))
        return 1
    print(f"boundaries ok ({len(RULES)} packages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
