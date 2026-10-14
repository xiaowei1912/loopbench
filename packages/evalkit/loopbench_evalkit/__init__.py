"""Evaluation harness. Discovers simulators, policies, and suites at runtime."""

from loopbench_evalkit.loop import run_closed_loop
from loopbench_evalkit.runner import evaluate

__all__ = ["evaluate", "run_closed_loop"]
