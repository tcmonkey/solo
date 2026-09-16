#!/usr/bin/env python3
"""Initialize a non-destructive Solo workspace in a target project."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


PHASES = [
    "intake", "requirements", "product", "ui", "technical", "planning",
    "development", "code_review", "testing", "release", "retrospective",
]

ENABLED = {
    "lite": {"intake", "requirements", "technical", "planning", "development", "code_review", "testing"},
    "standard": {
        "intake", "requirements", "product", "technical", "planning",
        "development", "code_review", "testing", "release",
    },
    "full": set(PHASES),
}

COMMON_ASSETS = [
    "project-profile.yaml",
    "00 输入材料清单.md",
    "01 需求文档.md",
    "04 技术方案.md",
    "05 开发计划.md",
    "06 开发自测报告.md",
    "07 代码审查报告.md",
    "08 测试用例.md",
    "09 测试报告.md",
    "10 缺陷记录.md",
    "14 交付追踪矩阵.md",
    "15 决策记录.md",
    "16 假设记录.md",
    "17 开放问题.md",
    "18 交接记录.md",
]

MODE_ASSETS = {
    "lite": [],
    "standard": ["02 产品方案.md", "12 发布检查单.md"],
    "full": ["02 产品方案.md", "03 界面设计方案.md", "11 性能测试报告.md", "12 发布检查单.md", "13 项目复盘.md"],
}

CAPABILITY_KEYS = ("filesystem", "shell", "python", "repository", "browser", "persistence")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Target project root")
    parser.add_argument("--mode", choices=sorted(ENABLED), default="standard")
    parser.add_argument("--interaction", choices=("guided", "continuous"), default="guided")
    parser.add_argument("--platform", default="unknown", help="Agent host runtime")
    parser.add_argument("--model", default="unknown", help="Model name when known")
    parser.add_argument(
        "--capability", action="append", default=[], metavar="KEY=VALUE",
        help="Detected runtime capability; may be repeated",
    )
    return parser.parse_args()


def parse_capabilities(entries: list[str]) -> dict[str, str]:
    capabilities = {key: "unknown" for key in CAPABILITY_KEYS}
    for entry in entries:
        key, separator, value = entry.partition("=")
        if not separator or key not in capabilities or not value.strip():
            allowed = ", ".join(CAPABILITY_KEYS)
            raise SystemExit(f"Invalid capability {entry!r}; expected KEY=VALUE where KEY is one of: {allowed}")
        capabilities[key] = value.strip()
    if capabilities["filesystem"] == "unknown":
        capabilities["filesystem"] = "read-write"
    if capabilities["python"] == "unknown":
        capabilities["python"] = Path(sys.executable).name
    return capabilities


def render(text: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def main() -> int:
    args = parse_args()
    capabilities = parse_capabilities(args.capability)
    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        raise SystemExit(f"Project directory does not exist: {project}")

    skill_dir = Path(__file__).resolve().parent.parent
    if project == skill_dir or skill_dir in project.parents:
        raise SystemExit("Refusing to initialize inside the solo skill directory")

    delivery = project / ".ai-delivery"
    ai_root = project / "AI"
    input_dir = ai_root / "input"
    output_dir = ai_root / "output"
    if delivery.exists():
        raise SystemExit(f"Delivery workspace already exists: {delivery}")

    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    values = {
        "PROJECT_NAME": project.name,
        "PROJECT_ROOT": str(project),
        "DELIVERY_MODE": args.mode,
        "INTERACTION_MODE": args.interaction,
        "CREATED_AT": now,
        "PLATFORM": args.platform,
        "MODEL": args.model,
        "CAP_FILESYSTEM": capabilities["filesystem"],
        "CAP_SHELL": capabilities["shell"],
        "CAP_PYTHON": capabilities["python"],
        "CAP_REPOSITORY": capabilities["repository"],
        "CAP_BROWSER": capabilities["browser"],
        "CAP_PERSISTENCE": capabilities["persistence"],
    }

    assets = skill_dir / "assets"
    selected = list(dict.fromkeys(COMMON_ASSETS + MODE_ASSETS[args.mode]))
    destinations: dict[str, Path] = {}
    for name in selected:
        if name == "project-profile.yaml":
            destination = delivery / name
        elif name == "00 输入材料清单.md":
            destination = input_dir / name
        else:
            destination = output_dir / name
        destinations[name] = destination
    conflicts = [str(destination) for destination in destinations.values() if destination.exists()]
    if conflicts:
        raise SystemExit("Initialization would overwrite existing files: " + ", ".join(conflicts))

    delivery.mkdir(parents=True)
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    for name, destination in destinations.items():
        source = assets / name
        destination.write_text(render(source.read_text(encoding="utf-8"), values), encoding="utf-8")

    state_template = json.loads(render((assets / "state.json").read_text(encoding="utf-8"), values))
    state_template["phases"] = {
        phase: {
            "status": "not_started" if phase in ENABLED[args.mode] else "skipped",
            "required": phase in ENABLED[args.mode],
            "approved_at": None,
        }
        for phase in PHASES
    }
    state_template["phases"]["intake"]["status"] = "in_progress"
    (delivery / "state.json").write_text(
        json.dumps(state_template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"Initialized {delivery}")
    print(f"Mode: {args.mode}; interaction: {args.interaction}")
    print(f"Runtime: {args.platform}; model: {args.model}")
    print("Next: ingest sources and complete AI/output/01 需求文档.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
