#!/usr/bin/env python3
"""Migrate a Solo project to the 0.7 numbered Chinese document layout safely."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


TARGET_VERSION = "0.7.0"
TARGET_SCHEMA = "1.4"
CAPABILITY_KEYS = ("filesystem", "shell", "python", "repository", "browser", "persistence")
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

OUTPUT_RENAMES = {
    "requirements.md": "01 需求文档.md",
    "product-spec.md": "02 产品方案.md",
    "ui-spec.md": "03 界面设计方案.md",
    "technical-design.md": "04 技术方案.md",
    "implementation-plan.md": "05 开发计划.md",
    "development-report.md": "06 开发自测报告.md",
    "code-review-report.md": "07 代码审查报告.md",
    "review-report.md": "07 旧版代码审查记录.md",
    "test-cases.md": "08 测试用例.md",
    "test-report.md": "09 测试报告.md",
    "defect-log.md": "10 缺陷记录.md",
    "performance-report.md": "11 性能测试报告.md",
    "release-checklist.md": "12 发布检查单.md",
    "retrospective.md": "13 项目复盘.md",
}
ROOT_RENAMES = {
    "traceability.md": "14 交付追踪矩阵.md",
    "decisions.md": "15 决策记录.md",
    "assumptions.md": "16 假设记录.md",
    "open-questions.md": "17 开放问题.md",
    "handoff.md": "18 交接记录.md",
}
CURRENT_OUTPUT_RENAMES = {
    "需求文档.md": "01 需求文档.md",
    "产品方案.md": "02 产品方案.md",
    "界面设计方案.md": "03 界面设计方案.md",
    "技术方案.md": "04 技术方案.md",
    "开发计划.md": "05 开发计划.md",
    "开发自测报告.md": "06 开发自测报告.md",
    "代码审查报告.md": "07 代码审查报告.md",
    "测试用例.md": "08 测试用例.md",
    "测试报告.md": "09 测试报告.md",
    "缺陷记录.md": "10 缺陷记录.md",
    "性能测试报告.md": "11 性能测试报告.md",
    "发布检查单.md": "12 发布检查单.md",
    "项目复盘.md": "13 项目复盘.md",
}
CURRENT_ROOT_RENAMES = {
    "交付追踪矩阵.md": "14 交付追踪矩阵.md",
    "决策记录.md": "15 决策记录.md",
    "假设记录.md": "16 假设记录.md",
    "开放问题.md": "17 开放问题.md",
    "交接记录.md": "18 交接记录.md",
}
REQUIRED_OUTPUT = [
    "01 需求文档.md", "04 技术方案.md", "05 开发计划.md", "06 开发自测报告.md",
    "07 代码审查报告.md", "08 测试用例.md", "09 测试报告.md", "10 缺陷记录.md",
    "14 交付追踪矩阵.md", "15 决策记录.md", "16 假设记录.md", "17 开放问题.md", "18 交接记录.md",
]
MODE_OUTPUT = {
    "lite": [],
    "standard": ["02 产品方案.md", "12 发布检查单.md"],
    "full": ["02 产品方案.md", "03 界面设计方案.md", "11 性能测试报告.md", "12 发布检查单.md", "13 项目复盘.md"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Target project root")
    return parser.parse_args()


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def render(text: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def phase_record(value: object, required: bool) -> dict[str, object]:
    record = dict(value) if isinstance(value, dict) else {}
    record.setdefault("status", "not_started" if required else "skipped")
    record.setdefault("required", required)
    record.setdefault("approved_at", None)
    return record


def split_verification_status(status: str, required: bool) -> str:
    if not required:
        return "skipped"
    if status == "not_started":
        return "not_started"
    if status == "blocked":
        return "blocked"
    return "stale"


def unique_existing(candidates: list[Path]) -> list[Path]:
    found: list[Path] = []
    resolved: set[Path] = set()
    for candidate in candidates:
        if candidate.is_file():
            real = candidate.resolve()
            if real not in resolved:
                resolved.add(real)
                found.append(candidate)
    return found


def move_document(candidates: list[Path], destination: Path, backup_documents: Path) -> None:
    sources = unique_existing(candidates)
    if destination.is_file():
        destination_bytes = destination.read_bytes()
        for source in sources:
            if source.resolve() == destination.resolve():
                continue
            if source.read_bytes() != destination_bytes:
                raise SystemExit(f"Document naming conflict: {source} and {destination}")
            backup = backup_documents / source.name
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, backup)
            source.unlink()
        return
    if not sources:
        return
    primary = sources[0]
    destination.parent.mkdir(parents=True, exist_ok=True)
    backup_documents.mkdir(parents=True, exist_ok=True)
    shutil.copy2(primary, backup_documents / primary.name)
    os.replace(primary, destination)
    for duplicate in sources[1:]:
        if duplicate.read_bytes() != destination.read_bytes():
            raise SystemExit(f"Document naming conflict: {duplicate} and {destination}")
        shutil.copy2(duplicate, backup_documents / duplicate.name)
        duplicate.unlink()


def main() -> int:
    project = Path(parse_args().project).expanduser().resolve()
    delivery = project / ".ai-delivery"
    state_path = delivery / "state.json"
    profile_path = delivery / "project-profile.yaml"
    if not state_path.is_file():
        raise SystemExit(f"Delivery state not found: {state_path}")

    state = json.loads(state_path.read_text(encoding="utf-8"))
    current_version = str(state.get("template_version", "0.1.0"))
    if current_version == TARGET_VERSION:
        print(f"Project already uses template version {TARGET_VERSION}: {delivery}")
        return 0
    if not current_version.startswith(("0.1", "0.2", "0.3", "0.4", "0.5", "0.6")):
        raise SystemExit(f"Automatic migration supports 0.1.x through 0.6.x, found {current_version}")

    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    backup_name = f"{current_version}-to-{TARGET_VERSION}-{now.replace(':', '').replace('+', '-')}"
    backup_dir = delivery / "migrations" / backup_name
    backup_documents = backup_dir / "documents"
    backup_dir.mkdir(parents=True)
    shutil.copy2(state_path, backup_dir / "state.json")
    if profile_path.is_file():
        shutil.copy2(profile_path, backup_dir / "project-profile.yaml")

    input_dir = project / "AI/input"
    output_dir = project / "AI/output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    legacy_artifacts = delivery / "artifacts"
    for old_name, new_name in {**OUTPUT_RENAMES, **CURRENT_OUTPUT_RENAMES}.items():
        move_document(
            [legacy_artifacts / old_name, output_dir / old_name],
            output_dir / new_name,
            backup_documents,
        )
    for old_name, new_name in {**ROOT_RENAMES, **CURRENT_ROOT_RENAMES}.items():
        move_document(
            [delivery / old_name, output_dir / old_name],
            output_dir / new_name,
            backup_documents,
        )
    move_document(
        [
            delivery / "inputs/source-manifest.md",
            input_dir / "source-manifest.md",
            input_dir / "输入材料清单.md",
        ],
        input_dir / "00 输入材料清单.md",
        backup_documents,
    )

    mode = str(state.get("delivery_mode", "standard"))
    if mode not in ENABLED:
        mode = "standard"
        state["delivery_mode"] = mode
    enabled = ENABLED[mode]
    old_phases = state.get("phases") if isinstance(state.get("phases"), dict) else {}
    old_implementation = old_phases.get("implementation", old_phases.get("development", {}))
    old_verification = old_phases.get("verification", {})
    verification_status = (
        str(old_verification.get("status", "not_started"))
        if isinstance(old_verification, dict) else "not_started"
    )

    phases: dict[str, dict[str, object]] = {}
    for phase in PHASES:
        required = phase in enabled
        if phase == "development":
            phases[phase] = phase_record(old_implementation, required)
        elif phase in {"code_review", "testing"}:
            existing = old_phases.get(phase)
            if isinstance(existing, dict):
                phases[phase] = phase_record(existing, required)
            else:
                phases[phase] = phase_record({}, required)
                phases[phase]["status"] = split_verification_status(verification_status, required)
        else:
            phases[phase] = phase_record(old_phases.get(phase), required)

    verification_was_progressed = (
        current_version.startswith(("0.1", "0.2", "0.3"))
        and verification_status not in {"not_started", "skipped"}
    )
    if verification_was_progressed:
        for downstream in ("release", "retrospective"):
            if phases[downstream]["status"] in {"review", "approved", "complete"}:
                phases[downstream]["status"] = "stale"

    old_current = str(state.get("current_phase", "intake"))
    current_phase = {"implementation": "development", "verification": "code_review"}.get(old_current, old_current)
    if verification_was_progressed and old_current in {"verification", "release", "retrospective"}:
        current_phase = "code_review"
    if current_phase not in phases:
        current_phase = "intake"

    skill_dir = Path(__file__).resolve().parent.parent
    values = {
        "PROJECT_NAME": str(state.get("project_name", project.name)),
        "PROJECT_ROOT": str(project),
        "DELIVERY_MODE": mode,
        "INTERACTION_MODE": str(state.get("interaction_mode", "guided")),
        "CREATED_AT": now,
    }
    for name in list(dict.fromkeys(REQUIRED_OUTPUT + MODE_OUTPUT[mode])):
        destination = output_dir / name
        if not destination.exists():
            atomic_write(destination, render((skill_dir / "assets" / name).read_text(encoding="utf-8"), values))
    manifest_path = input_dir / "00 输入材料清单.md"
    if not manifest_path.exists():
        atomic_write(
            manifest_path,
            render((skill_dir / "assets/00 输入材料清单.md").read_text(encoding="utf-8"), values),
        )

    current_revision = state.get("revision") if isinstance(state.get("revision"), int) else -1
    next_revision = current_revision + 1
    state["template_version"] = TARGET_VERSION
    state["schema_version"] = TARGET_SCHEMA
    state["revision"] = next_revision
    state["current_phase"] = current_phase
    state["phases"] = phases
    runtime = state.get("runtime") if isinstance(state.get("runtime"), dict) else {}
    runtime.setdefault("platform", "migration")
    runtime.setdefault("model", "unknown")
    capabilities = runtime.get("capabilities") if isinstance(runtime.get("capabilities"), dict) else {}
    for key in CAPABILITY_KEYS:
        capabilities.setdefault(key, "unknown")
    runtime["capabilities"] = capabilities
    state["runtime"] = runtime
    state["last_actor"] = {"platform": "migration", "model": "unknown", "updated_at": now}
    state["handoff"] = {
        "summary": f"从 {current_version} 升级到 {TARGET_VERSION}，交付文档统一为带序号的中文文件名",
        "next_action": "重新加载当前阶段并校验带序号的中文文档路径",
    }
    state["last_updated"] = now

    handoff_path = output_dir / "18 交接记录.md"
    handoff = handoff_path.read_text(encoding="utf-8")
    if not handoff.endswith("\n"):
        handoff += "\n"
    handoff += (
        f"| {next_revision} | {now} | migration | unknown | {current_phase} | "
        f"从 {current_version} 升级到 {TARGET_VERSION}，文档迁移到 AI/input 与 AI/output 并统一为带序号的中文名 | "
        "重新读取当前阶段并校验产物 |\n"
    )
    atomic_write(handoff_path, handoff)
    atomic_write(state_path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")

    if profile_path.is_file():
        profile = profile_path.read_text(encoding="utf-8")
        if "template_version:" not in profile:
            profile = f'template_version: "{TARGET_VERSION}"\n' + profile
        if "schema_version:" not in profile:
            profile = f'schema_version: "{TARGET_SCHEMA}"\n' + profile
        profile = re.sub(
            r'(?m)^template_version:\s*["\']?[^"\'\n]+["\']?\s*$',
            f'template_version: "{TARGET_VERSION}"', profile, count=1,
        )
        profile = re.sub(
            r'(?m)^schema_version:\s*["\']?[^"\'\n]+["\']?\s*$',
            f'schema_version: "{TARGET_SCHEMA}"', profile, count=1,
        )
        if "input_dir:" not in profile:
            profile = profile.replace("delivery:\n", 'delivery:\n  input_dir: "AI/input"\n', 1)
        if "output_dir:" not in profile:
            profile = profile.replace("delivery:\n", 'delivery:\n  output_dir: "AI/output"\n', 1)
        profile = re.sub(r'(?m)^\s+artifact_bridge:.*\n?', "", profile)
        if "compatibility:" not in profile:
            profile += (
                "\ncompatibility:\n"
                "  artifact_layout: \"AI-directories\"\n"
                "  state_owner: \".ai-delivery\"\n"
                "  skill_standard: \"agent-skills\"\n"
                "  runtime_binding: \"dynamic\"\n"
                "  concurrent_agents: false\n"
            )
        elif "artifact_layout:" not in profile:
            profile = profile.replace("compatibility:\n", 'compatibility:\n  artifact_layout: "AI-directories"\n', 1)
        if "quality:" not in profile:
            profile += "\nquality:\n"
        if "require_developer_self_test:" not in profile:
            profile = profile.replace("quality:\n", "quality:\n  require_developer_self_test: true\n", 1)
        if "require_independent_testing:" not in profile:
            profile = profile.replace("quality:\n", "quality:\n  require_independent_testing: true\n", 1)
        if "performance_testing:" not in profile:
            profile = profile.replace("quality:\n", 'quality:\n  performance_testing: "auto"\n', 1)
        profile = re.sub(r"(?m)^\s+require_tests:\s*.*\n?", "", profile)
        if re.search(r"(?m)^updated_at:\s*", profile):
            profile = re.sub(r"(?m)^updated_at:\s*.*$", f'updated_at: "{now}"', profile, count=1)
        else:
            profile += f'\nupdated_at: "{now}"\n'
        atomic_write(profile_path, profile)
    else:
        atomic_write(
            profile_path,
            render((skill_dir / "assets/project-profile.yaml").read_text(encoding="utf-8"), values),
        )

    for legacy_link in (delivery / "artifacts", delivery / "inputs"):
        if legacy_link.is_symlink():
            legacy_link.unlink()
        elif legacy_link.is_dir():
            try:
                legacy_link.rmdir()
            except OSError:
                pass

    print(f"Migrated {delivery} to template version {TARGET_VERSION}")
    print(f"Backup: {backup_dir}")
    if verification_was_progressed:
        print("Previous combined verification was marked stale for separate CR and testing review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
