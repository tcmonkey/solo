#!/usr/bin/env python3
"""只读查询本机 Codex app-server，确认 Solo 已进入真实技能发现列表。"""

from __future__ import annotations

import argparse
import json
import selectors
import shutil
import subprocess
import time
from pathlib import Path

from build_distributions import ROOT


def response(process, selector, request_id, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not selector.select(max(0, deadline - time.monotonic())):
            break
        line = process.stdout.readline()
        if not line:
            raise RuntimeError("Codex app-server closed its output")
        data = json.loads(line)
        if data.get("id") == request_id:
            if "error" in data:
                raise RuntimeError(str(data["error"]))
            return data["result"]
    raise RuntimeError(f"Timed out waiting for Codex response {request_id}")


def send(process, data):
    process.stdin.write(json.dumps(data) + "\n")
    process.stdin.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    bundled = Path("/Applications/ChatGPT.app/Contents/Resources/codex")
    parser.add_argument("--executable", default=str(bundled) if bundled.is_file() else shutil.which("codex"))
    parser.add_argument("--cwd", default=str(ROOT.parent))
    args = parser.parse_args()
    if not args.executable:
        parser.exit(1, "Codex executable not found; specify --executable\n")
    process = subprocess.Popen([args.executable, "app-server", "--stdio"], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            send(process, {"id": 1, "method": "initialize", "params": {
                "clientInfo": {"name": "solo-install-verification", "version": "1.0"},
                "capabilities": {"experimentalApi": True}}})
            response(process, selector, 1)
            send(process, {"method": "initialized", "params": {}})
            send(process, {"id": 2, "method": "skills/list", "params": {
                "cwds": [str(Path(args.cwd).resolve())], "forceReload": True}})
            result = response(process, selector, 2)
        entries = result.get("data", [])
        skills = [skill for entry in entries for skill in entry.get("skills", []) if skill.get("name") == "solo"]
        errors = [error for entry in entries for error in entry.get("errors", [])]
        print(json.dumps({"solo_count": len(skills), "skills": skills, "discovery_errors": errors},
                         ensure_ascii=False, indent=2))
        return 0 if len(skills) == 1 and skills[0].get("enabled", True) and not errors else 1
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Discovery check failed: {error}")
        return 1
    finally:
        # 只终止本脚本启动的诊断进程，不影响正在运行的桌面应用。
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
