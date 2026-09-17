#!/usr/bin/env python3
"""校验 solo 的结构、按需产物和阶段隔离；不代替语义评审或真实验收。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from delivery_model import (CAPABILITY_KEYS, GOAL_LABELS, MODE_LABELS, PHASE_FILES, PHASES,
                            RELEASE_PHASES, SCHEMA_VERSION, TEMPLATE_VERSION, VALID_STATES, WORKBENCH)

ACTIVE = {"in_progress", "review", "approved", "complete", "stale"}
DONE = {"approved", "complete"}
SECTIONS = {
    "planning": "开发计划", "development": "实际变更",
    "developer_self_test": "开发自测", "code_review": "代码审查",
    "testing": "测试用例", "release_preparation": "发布准备",
    "initial_release": "初始发布", "observation": "观测",
    "rollout": "放量", "full_release": "完整发布",
    "effect_evaluation": "效果",
}


def check_frontmatter(path: Path, errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not match:
        errors.append(f"{path}: missing YAML frontmatter")
        return
    for field in ("project", "artifact", "status", "version", "updated"):
        if not re.search(rf"(?m)^{field}:", match[1]):
            errors.append(f"{path}: missing metadata field {field}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--phase", choices=["all", *PHASES], default="all")
    args = parser.parse_args()
    project = Path(args.project).expanduser().resolve()
    delivery = project / ".ai-delivery"
    errors, warnings = [], []
    required = [".ai-delivery/state.json", ".ai-delivery/project-profile.yaml",
                "AI/input/00 输入材料清单.md", "AI/output/" + WORKBENCH]
    for relative in required:
        if not (project / relative).is_file():
            errors.append(f"Missing required file: {relative}")
    state = None
    state_path = delivery / "state.json"
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid state JSON: {exc}")
    if not isinstance(state, dict):
        errors.append("state.json must be an object")
        state = {}
    else:
        if state.get("template_version") != TEMPLATE_VERSION or state.get("schema_version") != SCHEMA_VERSION:
            errors.append(f"Unsupported template/schema; run migrate_project.py for {TEMPLATE_VERSION}/{SCHEMA_VERSION}")
        if state.get("artifact_layout") != "consolidated-lazy":
            errors.append("artifact_layout must be consolidated-lazy")
        if not isinstance(state.get("delivery_mode"), str) or state.get("delivery_mode") not in MODE_LABELS:
            errors.append("Invalid delivery_mode")
        # 终点是向后兼容可选字段，不从缺失值重建审批或阶段状态。
        goal = state.get("execution_goal", "auto")
        if not isinstance(goal, str) or goal not in GOAL_LABELS:
            errors.append("Invalid execution_goal")
        phases = state.get("phases", {})
        if not isinstance(phases, dict):
            phases = {}
            errors.append("phases must be an object")
        for phase in PHASES:
            data = phases.get(phase, {})
            if not isinstance(data, dict) or data.get("status") not in VALID_STATES:
                errors.append(f"Missing/invalid phase status: {phase}")
            elif not isinstance(data.get("required"), bool):
                errors.append(f"Phase required must be boolean: {phase}")
        if state.get("current_phase") not in PHASES:
            errors.append("Invalid current_phase")
        revision = state.get("revision")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
            errors.append("Invalid revision")
        if not isinstance(state.get("approvals"), list):
            errors.append("approvals must be an array")
        runtime = state.get("runtime")
        if not isinstance(runtime, dict) or not runtime.get("platform") or not runtime.get("model"):
            errors.append("Missing runtime platform/model")
        else:
            caps = runtime.get("capabilities")
            if not isinstance(caps, dict) or set(CAPABILITY_KEYS) - caps.keys():
                errors.append("Missing runtime capabilities")
        overrides = state.get("artifact_overrides", {})
        if not isinstance(overrides, dict):
            errors.append("artifact_overrides must be an object")
            overrides = {}
        checked = set()
        for phase in (PHASES if args.phase == "all" else [args.phase]):
            relative = overrides.get(phase, "AI/output/" + PHASE_FILES[phase])
            if not isinstance(relative, str):
                errors.append(f"Invalid artifact override: {phase}")
                continue
            path = (project / relative).resolve()
            if not path.is_relative_to((project / "AI/output").resolve()) or path.suffix != ".md":
                errors.append(f"Artifact path must stay in AI/output and be Markdown: {phase}")
                continue
            data = phases.get(phase, {})
            status = data.get("status") if isinstance(data, dict) else None
            if status in ACTIVE and not path.is_file():
                errors.append(f"Active artifact missing for {phase}: {relative}")
            if path.is_file():
                if path not in checked:
                    check_frontmatter(path, errors)
                    checked.add(path)
                text = path.read_text(encoding="utf-8")
                section = SECTIONS.get(phase)
                if phase == "product" and relative.endswith("01 需求文档.md"):
                    section = "产品方案"
                if status in ACTIVE and section and not re.search(rf"(?m)^#{{1,6}} .*{section}", text):
                    errors.append(f"{relative}: missing phase section {section}")
                if status in DONE and "TBD" in text:
                    warnings.append(f"{relative}: contains TBD; judge only the completed phase section")
        # 合并文件不意味着阶段合并；审查、测试和实际发布的前置关口各自校验。
        gates = {
            "developer_self_test": ["development"],
            "code_review": ["developer_self_test"],
            "testing": ["code_review"],
            "release_preparation": ["testing"],
            "initial_release": ["release_preparation"],
            "observation": ["initial_release"],
            "rollout": ["observation"],
            "full_release": ["initial_release", "observation", "rollout"],
            "effect_evaluation": ["full_release"] if phases.get("full_release", {}).get("required") else [],
        }
        for phase, prerequisites in gates.items():
            if phases.get(phase, {}).get("status") in DONE:
                for prerequisite in prerequisites:
                    entry = phases.get(prerequisite, {})
                    if entry.get("status") not in DONE and not (
                        entry.get("status") == "skipped" and entry.get("note")
                    ):
                        errors.append(f"{phase} cannot complete before {prerequisite}; no completion evidence or skip reason")
        for phase, data in phases.items():
            if isinstance(data, dict) and data.get("status") == "skipped" and data.get("required") and not data.get("note"):
                errors.append(f"Required phase skipped without reason: {phase}")
    workbench = project / "AI/output" / WORKBENCH
    if workbench.is_file():
        check_frontmatter(workbench, errors)
        text = workbench.read_text(encoding="utf-8")
        handoff_section = text.split("## 7. 交接记录", 1)[-1] if "## 7. 交接记录" in text else ""
        if not re.search(rf"(?m)^\| {state.get('revision')} \|", handoff_section):
            errors.append("交付工作台缺少第 7 节或当前 revision 的交接行")
    profile = delivery / "project-profile.yaml"
    if profile.is_file():
        profile_text = profile.read_text(encoding="utf-8")
        match = re.search(r'(?m)^  execution_goal:\s*["\']?([^"\'\s]+)["\']?\s*$', profile_text)
        if re.search(r'(?m)^  execution_goal:', profile_text) and not match:
            errors.append("project-profile.yaml invalid execution_goal")
        if match and match[1] != state.get("execution_goal", "auto"):
            errors.append("project-profile.yaml execution_goal is inconsistent with state")
        elif not match and state.get("execution_goal", "auto") != "auto":
            errors.append("project-profile.yaml missing execution_goal")
        for key, value in (("template_version", TEMPLATE_VERSION), ("schema_version", SCHEMA_VERSION)):
            if not re.search(rf'(?m)^{key}:\s*["\']?{re.escape(value)}["\']?\s*$', profile_text):
                errors.append(f"project-profile.yaml {key} is inconsistent")
    for name in (".handoff-transaction.json", ".migration-transaction.json"):
        if (delivery / name).exists():
            errors.append(f"Pending transaction requires recovery: {name}")
    for warning in sorted(set(warnings)):
        print("Warning: " + warning)
    for error in errors:
        print("Error: " + error)
    if not errors:
        print(f"Delivery workspace is structurally valid: {delivery}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
