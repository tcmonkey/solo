#!/usr/bin/env python3
"""Validate structural invariants of a project's Solo workspace."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


EXPECTED_TEMPLATE_VERSION = "0.7.0"
EXPECTED_SCHEMA_VERSION = "1.4"
CAPABILITY_KEYS = {"filesystem", "shell", "python", "repository", "browser", "persistence"}

REQUIRED_FILES = [
    ".ai-delivery/state.json",
    ".ai-delivery/project-profile.yaml",
    "AI/output/14 交付追踪矩阵.md",
    "AI/output/15 决策记录.md",
    "AI/output/16 假设记录.md",
    "AI/output/17 开放问题.md",
    "AI/output/18 交接记录.md",
    "AI/input/00 输入材料清单.md",
]

PHASE_FILES = {
    "requirements": "AI/output/01 需求文档.md",
    "product": "AI/output/02 产品方案.md",
    "ui": "AI/output/03 界面设计方案.md",
    "technical": "AI/output/04 技术方案.md",
    "planning": "AI/output/05 开发计划.md",
    "development": "AI/output/06 开发自测报告.md",
    "code_review": "AI/output/07 代码审查报告.md",
    "testing": "AI/output/09 测试报告.md",
    "release": "AI/output/12 发布检查单.md",
    "retrospective": "AI/output/13 项目复盘.md",
}

SUPPLEMENTAL_PHASE_FILES = {
    "testing": ["AI/output/08 测试用例.md", "AI/output/10 缺陷记录.md"],
}

VALID_STATES = {"not_started", "in_progress", "review", "approved", "skipped", "stale", "blocked", "complete"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Target project root")
    parser.add_argument("--phase", choices=["all", *PHASE_FILES], default="all")
    return parser.parse_args()


def check_frontmatter(path: Path, errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        errors.append(f"{path}: missing YAML frontmatter")
    for field in ("project:", "artifact:", "status:", "version:", "updated:"):
        if not re.search(rf"(?m)^{re.escape(field)}", text):
            errors.append(f"{path}: missing metadata field {field[:-1]}")


def main() -> int:
    args = parse_args()
    project = Path(args.project).expanduser().resolve()
    delivery = project / ".ai-delivery"
    errors: list[str] = []
    warnings: list[str] = []

    if not delivery.is_dir():
        raise SystemExit(f"Delivery workspace not found: {delivery}")

    for relative in REQUIRED_FILES:
        if not (project / relative).is_file():
            errors.append(f"Missing required file: {relative}")

    state_path = delivery / "state.json"
    state = None
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"state.json is invalid JSON: {exc}")

    if state:
        phases = state.get("phases", {})
        current = state.get("current_phase")
        revision = state.get("revision")
        if state.get("template_version") != EXPECTED_TEMPLATE_VERSION:
            errors.append(
                f"Unsupported template version: {state.get('template_version')}; "
                f"expected {EXPECTED_TEMPLATE_VERSION}. Run migrate_project.py first."
            )
        if state.get("schema_version") != EXPECTED_SCHEMA_VERSION:
            errors.append(
                f"Unsupported state schema version: {state.get('schema_version')}; "
                f"expected {EXPECTED_SCHEMA_VERSION}."
            )
        if not isinstance(revision, int) or revision < 0:
            errors.append(f"Invalid non-negative revision: {revision}")
        if current not in phases:
            errors.append(f"Current phase is missing from phases: {current}")
        runtime = state.get("runtime")
        if not isinstance(runtime, dict):
            errors.append("state.json is missing runtime information")
        else:
            if not runtime.get("platform") or not runtime.get("model"):
                errors.append("runtime platform and model must be non-empty")
            capabilities = runtime.get("capabilities")
            if not isinstance(capabilities, dict):
                errors.append("runtime capabilities must be an object")
            else:
                missing_capabilities = sorted(CAPABILITY_KEYS - capabilities.keys())
                if missing_capabilities:
                    errors.append(f"Missing runtime capabilities: {', '.join(missing_capabilities)}")
        for phase, data in phases.items():
            status = data.get("status") if isinstance(data, dict) else None
            if status not in VALID_STATES:
                errors.append(f"Invalid status for phase {phase}: {status}")

        targets = PHASE_FILES if args.phase == "all" else {args.phase: PHASE_FILES[args.phase]}
        for phase, relative in targets.items():
            phase_data = phases.get(phase, {})
            status = phase_data.get("status")
            artifact_path = project / relative
            if phase_data.get("required") and not artifact_path.is_file():
                errors.append(f"Required artifact missing for {phase}: {relative}")
            if artifact_path.is_file():
                check_frontmatter(artifact_path, errors)
                if status in {"review", "approved", "complete"} and "TBD" in artifact_path.read_text(encoding="utf-8"):
                    warnings.append(f"{relative}: contains TBD while phase is {status}")
            for supplemental in SUPPLEMENTAL_PHASE_FILES.get(phase, []):
                supplemental_path = project / supplemental
                if phase_data.get("required") and not supplemental_path.is_file():
                    errors.append(f"Required supporting artifact missing for {phase}: {supplemental}")
                elif supplemental_path.is_file():
                    check_frontmatter(supplemental_path, errors)

        performance_path = project / "AI/output/11 性能测试报告.md"
        if performance_path.is_file():
            check_frontmatter(performance_path, errors)

    manifest = project / "AI/input/00 输入材料清单.md"
    if manifest.is_file() and "SRC-" not in manifest.read_text(encoding="utf-8"):
        warnings.append("00 输入材料清单.md contains no source IDs")

    handoff = project / "AI/output/18 交接记录.md"
    if handoff.is_file() and state:
        revision_marker = f"| {state.get('revision')} |"
        if revision_marker not in handoff.read_text(encoding="utf-8"):
            errors.append("18 交接记录.md does not contain the current state revision")

    if (delivery / ".handoff-transaction.json").exists():
        errors.append("A pending handoff transaction requires recovery")
    if (delivery / ".handoff.lock").exists():
        warnings.append("A handoff writer lock is present")

    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")
    if errors:
        print("Errors:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Delivery workspace is structurally valid: {delivery}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
