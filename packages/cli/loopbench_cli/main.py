"""Operator CLI. `loopbench serve` is the product entry."""

from __future__ import annotations

import argparse
import json

import threading

from loopbench_evalkit.analysis import analyze
from loopbench_evalkit.experiment import load_experiment, run_experiment
from loopbench_evalkit.loop import run_closed_loop
from loopbench_evalkit.runner import evaluate
from loopbench_spec.composition import RunSpec
from loopbench_spec.registry import policies, simulator, simulators, suite, suites
from loopbench_transport.wire import RemotePolicy
from loopbench_transport.wire import serve as serve_policy


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="loopbench", description="Physical AI evaluation loop")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("catalog", help="list installed simulators, policies, and suites")

    eval_parser = sub.add_parser("eval", help="run one suite")
    _common(eval_parser)

    loop_parser = sub.add_parser("loop", help="evaluate, attribute, improve, evaluate again")
    _common(loop_parser)

    http = sub.add_parser("serve", help="start the HTTP API")
    http.add_argument("--host", default="0.0.0.0")
    http.add_argument("--port", type=int, default=43124)

    experiment = sub.add_parser("experiment", help="run an experiment file")
    experiment.add_argument("path")

    policy_serve = sub.add_parser("policy-serve", help="serve one policy over TCP")
    policy_serve.add_argument("--policy", default="oracle")
    policy_serve.add_argument("--host", default="127.0.0.1")
    policy_serve.add_argument("--port", type=int, default=43126)

    args = parser.parse_args(argv)
    if args.command == "catalog":
        _catalog()
    elif args.command == "eval":
        _eval(args)
    elif args.command == "loop":
        _loop(args)
    elif args.command == "experiment":
        _experiment(args)
    elif args.command == "policy-serve":
        _policy_serve(args)
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


def _open_policy(run: RunSpec):
    if run.endpoint:
        return RemotePolicy(run.endpoint, name=run.policy, needs_privileged=bool(run.needs_privileged))
    return policies()[run.policy].make()


def _experiment(args: argparse.Namespace) -> None:
    experiment = load_experiment(args.path)
    result = run_experiment(experiment, open_simulator=simulator, open_policy=_open_policy)
    print(json.dumps({"name": result["name"], "protocol": result["protocol"], "summary": result["summary"], "runs": result["runs"]}, ensure_ascii=False, indent=2))


def _policy_serve(args: argparse.Namespace) -> None:
    policy = policies()[args.policy].make()
    stop = threading.Event()
    print(f"policy {args.policy} on {args.host}:{args.port}", flush=True)
    try:
        serve_policy(policy, args.host, args.port, stop)
    except KeyboardInterrupt:
        stop.set()


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
