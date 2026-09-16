#!/usr/bin/env python3
"""Advance delivery state and append a recoverable, revision-protected handoff record."""

from __future__ import annotations

import argparse
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


CAPABILITY_KEYS = {"filesystem", "shell", "python", "repository", "browser", "persistence"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Target project root")
    parser.add_argument("--platform", required=True, help="Agent runtime, for example codex")
    parser.add_argument("--model", default="unknown", help="Model name when known")
    parser.add_argument("--phase", required=True, help="Current delivery phase")
    parser.add_argument("--summary", required=True, help="Short summary of completed work")
    parser.add_argument("--next-action", required=True, help="Exact next action")
    parser.add_argument("--expected-revision", required=True, type=int, help="Revision read before work")
    parser.add_argument(
        "--capability",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Detected runtime capability; may be repeated",
    )
    return parser.parse_args()


def table_cell(value: str) -> str:
    return " ".join(value.replace("|", "\\|").splitlines()).strip()


def atomic_write(path: Path, content: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def parse_capabilities(entries: list[str]) -> dict[str, str]:
    capabilities: dict[str, str] = {}
    for entry in entries:
        key, separator, value = entry.partition("=")
        if not separator or key not in CAPABILITY_KEYS or not value.strip():
            allowed = ", ".join(sorted(CAPABILITY_KEYS))
            raise SystemExit(f"Invalid capability {entry!r}; expected KEY=VALUE where KEY is one of: {allowed}")
        capabilities[key] = value.strip()
    return capabilities


@contextmanager
def exclusive_lock(path: Path):
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise SystemExit(f"Delivery workspace is locked by another writer: {path}") from exc
    try:
        os.write(descriptor, f"pid={os.getpid()}\n".encode())
        yield
    finally:
        os.close(descriptor)
        path.unlink(missing_ok=True)


def recover_transaction(transaction_path: Path, state_path: Path, handoff_path: Path) -> None:
    if not transaction_path.is_file():
        return
    transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
    state = json.loads(state_path.read_text(encoding="utf-8"))
    current_revision = state.get("revision")
    if current_revision not in {transaction.get("base_revision"), transaction.get("next_revision")}:
        raise SystemExit(
            f"Cannot recover pending handoff transaction at {transaction_path}; "
            f"state revision is {current_revision}"
        )
    atomic_write(handoff_path, transaction["handoff_content"])
    atomic_write(state_path, json.dumps(transaction["state"], ensure_ascii=False, indent=2) + "\n")
    transaction_path.unlink()
    print(f"Recovered pending handoff transaction at revision {transaction['next_revision']}")


def main() -> int:
    args = parse_args()
    capabilities = parse_capabilities(args.capability)
    delivery = Path(args.project).expanduser().resolve() / ".ai-delivery"
    state_path = delivery / "state.json"
    handoff_path = delivery.parent / "AI/output/18 交接记录.md"
    lock_path = delivery / ".handoff.lock"
    transaction_path = delivery / ".handoff-transaction.json"
    if not state_path.is_file() or not handoff_path.is_file():
        raise SystemExit("state.json or AI/output/18 交接记录.md is missing; initialize or migrate the project first")

    with exclusive_lock(lock_path):
        recover_transaction(transaction_path, state_path, handoff_path)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        current_revision = state.get("revision")
        if current_revision != args.expected_revision:
            raise SystemExit(
                f"Revision conflict: expected {args.expected_revision}, current {current_revision}. "
                "Reload and reconcile before recording a handoff."
            )
        if args.phase not in state.get("phases", {}):
            raise SystemExit(f"Unknown phase: {args.phase}")

        now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        next_revision = current_revision + 1
        row = (
            f"| {next_revision} | {table_cell(now)} | {table_cell(args.platform)} | "
            f"{table_cell(args.model)} | {table_cell(args.phase)} | "
            f"{table_cell(args.summary)} | {table_cell(args.next_action)} |\n"
        )
        handoff_content = handoff_path.read_text(encoding="utf-8")
        if not handoff_content.endswith("\n"):
            handoff_content += "\n"
        handoff_content += row

        state["revision"] = next_revision
        state["current_phase"] = args.phase
        state["runtime"] = state.get("runtime") or {"capabilities": {}}
        state["runtime"]["platform"] = args.platform
        state["runtime"]["model"] = args.model
        runtime_capabilities = state["runtime"].setdefault("capabilities", {})
        runtime_capabilities.update(capabilities)
        state["last_actor"] = {"platform": args.platform, "model": args.model, "updated_at": now}
        state["handoff"] = {"summary": args.summary, "next_action": args.next_action}
        state["last_updated"] = now

        transaction = {
            "base_revision": current_revision,
            "next_revision": next_revision,
            "state": state,
            "handoff_content": handoff_content,
        }
        atomic_write(transaction_path, json.dumps(transaction, ensure_ascii=False, indent=2) + "\n")
        atomic_write(handoff_path, handoff_content)
        atomic_write(state_path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")
        transaction_path.unlink()
    print(f"Recorded revision {next_revision} for {args.platform} at phase {args.phase}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
