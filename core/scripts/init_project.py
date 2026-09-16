#!/usr/bin/env python3
"""按需初始化 solo 工作区，不覆盖已有项目材料。"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from delivery_model import CAPABILITY_KEYS, ENABLED, PHASES, SCHEMA_VERSION, TEMPLATE_VERSION, WORKBENCH, ensure_project, render


def parse_capabilities(entries: list[str]) -> dict[str, str]:
    capabilities = {key: "unknown" for key in CAPABILITY_KEYS}
    for entry in entries:
        key, separator, value = entry.partition("=")
        if not separator or key not in capabilities or not value.strip():
            raise SystemExit(f"Invalid capability: {entry!r}")
        capabilities[key] = value.strip()
    if capabilities["filesystem"] == "unknown":
        capabilities["filesystem"] = "read-write"
    if capabilities["python"] == "unknown":
        capabilities["python"] = Path(sys.executable).name
    return capabilities


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--mode", choices=sorted(ENABLED), default="standard")
    parser.add_argument("--interaction", choices=("guided", "continuous"), default="guided")
    parser.add_argument("--platform", default="unknown")
    parser.add_argument("--model", default="unknown")
    parser.add_argument("--capability", action="append", default=[], metavar="KEY=VALUE")
    args = parser.parse_args()
    project = Path(args.project).expanduser().resolve()
    core = Path(__file__).resolve().parent.parent
    ensure_project(project, core)
    delivery = project / ".ai-delivery"
    if delivery.exists():
        raise SystemExit(f"Delivery workspace already exists: {delivery}")
    capabilities = parse_capabilities(args.capability)
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    values = {
        "PROJECT_NAME": project.name, "PROJECT_ROOT": str(project),
        "DELIVERY_MODE": args.mode, "INTERACTION_MODE": args.interaction,
        "CREATED_AT": now, "PLATFORM": args.platform, "MODEL": args.model,
        **{"CAP_" + key.upper(): value for key, value in capabilities.items()},
    }
    destinations = {
        "project-profile.yaml": delivery / "project-profile.yaml",
        "00 输入材料清单.md": project / "AI/input/00 输入材料清单.md",
        WORKBENCH: project / "AI/output" / WORKBENCH,
    }
    conflicts = [str(path) for path in destinations.values() if path.exists()]
    if conflicts:
        raise SystemExit("Initialization would overwrite existing files: " + ", ".join(conflicts))
    # 所有源模板和状态预先读取，避免因缺失资源生成半套目录。
    contents = {
        path: render((core / "assets" / name).read_text(encoding="utf-8"), values)
        for name, path in destinations.items()
    }
    state = json.loads(render((core / "assets/state.json").read_text(encoding="utf-8"), values))
    state.update(template_version=TEMPLATE_VERSION, schema_version=SCHEMA_VERSION,
                 artifact_layout="consolidated-lazy", artifact_overrides={})
    state["phases"] = {
        phase: {"status": "not_started" if phase in ENABLED[args.mode] else "skipped",
                "required": phase in ENABLED[args.mode], "approved_at": None}
        for phase in PHASES
    }
    state["phases"]["ui"]["note"] = "按界面变化启用；Full 也不强制生成 UI 文档"
    state["phases"]["intake"]["status"] = "in_progress"
    delivery.mkdir(parents=True)
    for path, content in contents.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (delivery / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Initialized {delivery}; mode={args.mode}; interaction={args.interaction}")
    print("仅创建输入清单和交付工作台；确认需求理解后再生成 01 需求文档.md。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
