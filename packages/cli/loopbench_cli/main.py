"""Operator CLI. `loopbench serve` is the product entry."""

from __future__ import annotations

import argparse
import json

from loopbench_evalkit.analysis import analyze
from loopbench_evalkit.loop import run_closed_loop
from loopbench_evalkit.runner import evaluate
from loopbench_spec.registry import policies, simulator, simulators, suite, suites


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="loopbench", description="Physical AI evaluation loop")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("catalog", help="list installed simulators, policies, and suites")

    eval_parser = sub.add_parser("eval", help="run one suite")
    _common(eval_parser)

    loop_parser = sub.add_parser("loop", help="evaluate, attribute, improve, evaluate again")
    _common(loop_parser)

    serve = sub.add_parser("serve", help="start the HTTP API")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=43124)

    args = parser.parse_args(argv)
    if args.command == "catalog":
        _catalog()
    elif args.command == "eval":
        _eval(args)
    elif args.command == "loop":
        _loop(args)
    elif args.command == "serve":
        import uvicorn

        uvicorn.run("loopbench_api.app:app", host=args.host, port=args.port, reload=False)


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--suite", default="tabletop_probe")
    parser.add_argument("--policy", default="vision_v1")
    parser.add_argument("--simulator", default="reference")
    parser.add_argument("--episodes", type=int, default=1)
    parser.add_argument("--seed", type=int, default=0)


def _catalog() -> None:
    print("simulators:", ", ".join(sorted(simulators())))
    print("policies:", ", ".join(sorted(policies())))
    print("suites:", ", ".join(sorted(suites())))


def _eval(args: argparse.Namespace) -> None:
    run = evaluate(
        simulator(args.simulator),
        policies()[args.policy].make(),
        suite(args.suite),
        episodes_per_cell=args.episodes,
        seed=args.seed,
    )
    report = analyze(run)
    print(json.dumps({"summary": run["summary"], "insights": report["insights"]}, ensure_ascii=False, indent=2))


def _loop(args: argparse.Namespace) -> None:
    result = run_closed_loop(
        args.suite,
        simulator_name=args.simulator,
        policy_name=args.policy,
        episodes_per_cell=args.episodes,
        seed=args.seed,
    )
    print(
        json.dumps(
            {"comparison": result["comparison"], "improve": result["improve"], "insights": result["analysis"]["insights"]},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
