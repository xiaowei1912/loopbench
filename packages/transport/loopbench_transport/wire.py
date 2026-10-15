"""One TCP connection, one JSON object per line.

The operations are the same ones XPolicyLab puts on a policy adapter:
reset the episode, then ask for an action. The transport is stdlib sockets
so a policy process does not share the simulator's dependencies.
"""

from __future__ import annotations

import json
import socket
import threading
from typing import Any

import numpy as np

from loopbench_transport.codec import from_jsonable, to_jsonable


def _readline(conn: socket.socket) -> bytes:
    chunks = []
    while True:
        byte = conn.recv(1)
        if not byte:
            return b""
        if byte == b"\n":
            return b"".join(chunks)
        chunks.append(byte)


def _send(conn: socket.socket, payload: dict) -> None:
    conn.sendall(json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n")


def _recv(conn: socket.socket) -> dict:
    line = _readline(conn)
    if not line:
        raise ConnectionError("policy connection closed")
    return json.loads(line)


def serve(
    policy,
    host: str,
    port: int,
    stop: threading.Event,
    *,
    ready: threading.Event | None = None,
    bound: list[int] | None = None,
) -> None:
    """Serve one policy until `stop` is set. Each client keeps one connection.

    `port` may be 0. The bound port is appended to `bound` and `ready` is set
    before the accept loop, so a test can connect without sleeping.
    """

    server = socket.create_server((host, port))
    server.settimeout(0.2)
    if bound is not None:
        bound.append(server.getsockname()[1])
    if ready is not None:
        ready.set()
    try:
        while not stop.is_set():
            try:
                conn, _addr = server.accept()
            except TimeoutError:
                continue
            except OSError:
                if stop.is_set():
                    break
                raise
            try:
                _session(conn, policy)
            finally:
                conn.close()
    finally:
        server.close()


def _session(conn: socket.socket, policy) -> None:
    while True:
        try:
            message = _recv(conn)
        except ConnectionError:
            return
        op = message.get("op")
        if op == "reset":
            policy.reset()
            _send(conn, {"ok": True})
        elif op == "act":
            observation = from_jsonable(message.get("observation") or {})
            info = from_jsonable(message.get("info"))
            action = np.asarray(policy.select_action(observation, info), dtype=np.float64).reshape(-1)
            _send(conn, {"ok": True, "action": [float(item) for item in action]})
        elif op == "close":
            _send(conn, {"ok": True})
            return
        else:
            _send(conn, {"ok": False, "error": f"unknown op {op!r}"})


class RemotePolicy:
    """Client side of the policy process. The eval runner treats it as a local policy."""

    def __init__(self, endpoint: str, *, name: str = "remote", needs_privileged: bool = False) -> None:
        host, _, port = endpoint.rpartition(":")
        if not host or not port:
            raise ValueError(f"Policy endpoint must be host:port, got {endpoint!r}.")
        self.endpoint = endpoint
        self.name = name
        self.needs_privileged = needs_privileged
        self.phase = "remote"
        self._sock = socket.create_connection((host, int(port)), timeout=10)
        self._sock.settimeout(30)

    def reset(self) -> None:
        reply = self._call({"op": "reset"})
        if not reply.get("ok"):
            raise RuntimeError(reply.get("error") or "remote reset failed")

    def select_action(self, observation: dict, info: dict | None = None) -> np.ndarray:
        reply = self._call(
            {
                "op": "act",
                "observation": to_jsonable(observation),
                "info": to_jsonable(info or {}),
            }
        )
        if not reply.get("ok"):
            raise RuntimeError(reply.get("error") or "remote act failed")
        return np.asarray(reply["action"], dtype=np.float64)

    def close(self) -> None:
        try:
            self._call({"op": "close"})
        except OSError:
            pass
        self._sock.close()

    def _call(self, payload: dict[str, Any]) -> dict:
        _send(self._sock, payload)
        return _recv(self._sock)
