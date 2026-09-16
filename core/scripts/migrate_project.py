#!/usr/bin/env python3
"""将 0.1～0.7 项目迁移到合并、按需的 0.8 文档布局；原文逐份归档。"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from delivery_model import CAPABILITY_KEYS, ENABLED, PHASE_FILES, PHASES, RELEASE_PHASES, SCHEMA_VERSION, TEMPLATE_VERSION, WORKBENCH, body, ensure_project, metadata, render
from record_handoff import atomic_write, exclusive_lock

OLD_NAMES = {
    "01 需求文档.md": ["需求文档.md", "requirements.md"],
    "02 产品方案.md": ["产品方案.md", "product-spec.md"],
    "03 界面设计方案.md": ["界面设计方案.md", "ui-spec.md"],
    "04 技术方案.md": ["技术方案.md", "technical-design.md"],
    "05 开发计划.md": ["开发计划.md", "implementation-plan.md"],
    "06 开发自测报告.md": ["开发自测报告.md", "development-report.md"],
    "07 代码审查报告.md": ["代码审查报告.md", "code-review-report.md", "review-report.md", "07 旧版代码审查记录.md"],
    "08 测试用例.md": ["测试用例.md", "test-cases.md"],
    "09 测试报告.md": ["测试报告.md", "test-report.md"],
    "10 缺陷记录.md": ["缺陷记录.md", "defect-log.md"],
    "11 性能测试报告.md": ["性能测试报告.md", "performance-report.md"],
    "12 发布检查单.md": ["发布检查单.md", "release-checklist.md"],
    "13 项目复盘.md": ["项目复盘.md", "retrospective.md"],
    "14 交付追踪矩阵.md": ["交付追踪矩阵.md", "traceability.md"],
    "15 决策记录.md": ["决策记录.md", "decisions.md"],
    "16 假设记录.md": ["假设记录.md", "assumptions.md"],
    "17 开放问题.md": ["开放问题.md", "open-questions.md"],
    "18 交接记录.md": ["交接记录.md", "handoff.md"],
}
GROUPS = {
    WORKBENCH: [("3. 需求追踪", "14 交付追踪矩阵.md"), ("4. 关键决策与审批", "15 决策记录.md"),
                ("5. 假设、开放问题与风险", "16 假设记录.md"), ("5. 假设、开放问题与风险补充", "17 开放问题.md")],
    "04 技术方案.md": [("整体方案（原文）", "04 技术方案.md"), ("开发计划", "05 开发计划.md")],
    "05 开发交付记录.md": [("实际变更与开发自测", "06 开发自测报告.md"), ("代码审查", "07 代码审查报告.md")],
    "06 测试验收报告.md": [("测试用例", "08 测试用例.md"), ("测试执行", "09 测试报告.md"),
                          ("缺陷与回归", "10 缺陷记录.md"), ("性能、兼容与回滚", "11 性能测试报告.md")],
    "07 发布运行记录.md": [("发布准备（旧记录）", "12 发布检查单.md")],
    "08 效果评估与复盘.md": [("效果评估与复盘（旧记录）", "13 项目复盘.md")],
}


def phase_record(value: object, required: bool) -> dict:
    record = dict(value) if isinstance(value, dict) else {}
    record.setdefault("status", "not_started" if required else "skipped")
    record.setdefault("required", required)
    record.setdefault("approved_at", None)
    return record


def recover(project: Path, journal: Path) -> None:
    project = project.resolve()
    transaction = json.loads(journal.read_text(encoding="utf-8"))
    state = json.loads((project / ".ai-delivery/state.json").read_text(encoding="utf-8"))
    if state.get("revision") not in {transaction["base_revision"], transaction["next_revision"]}:
        raise SystemExit("迁移恢复遇到较新状态，先协调 revision，不覆盖")
    # 只允许迁移写入 AI 文档或交付机器文件，不能越界覆盖代码。
    for relative, content in transaction["writes"].items():
        path = (project / relative).resolve()
        if not (path.is_relative_to(project / "AI") or path.is_relative_to(project / ".ai-delivery")):
            raise SystemExit(f"Unsafe migration destination: {relative}")
        if path.suffix not in {".md", ".json", ".yaml"}:
            raise SystemExit(f"Unsafe migration suffix: {relative}")
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(path, content)
    for relative, expected_sha in transaction["remove"].items():
        path = (project / relative).resolve()
        if not path.is_relative_to(project) or path.suffix != ".md" or relative in transaction["writes"]:
            raise SystemExit(f"Unsafe migration cleanup: {relative}")
        if path.is_file():
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
                raise SystemExit(f"迁移过程中原文被修改，保留文件并停止：{relative}")
            path.unlink()
    journal.unlink()
    print("迁移事务已完成，原文可从 migrations 归档恢复。")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    project = Path(parser.parse_args().project).expanduser().resolve()
    core = Path(__file__).resolve().parent.parent
    ensure_project(project, core)
    delivery = project / ".ai-delivery"
    state_path = delivery / "state.json"
    if not state_path.is_file():
        raise SystemExit(f"Missing delivery state: {state_path}")
    if (delivery / ".handoff-transaction.json").exists():
        raise SystemExit("先恢复待处理的交接事务，再迁移")
    journal = delivery / ".migration-transaction.json"
    with exclusive_lock(delivery / ".handoff.lock"):
        if journal.exists():
            recover(project, journal)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        old_version = str(state.get("template_version", "0.1.0"))
        if old_version == TEMPLATE_VERSION:
            print(f"Already at {TEMPLATE_VERSION}; no changes")
            return 0
        if not re.fullmatch(r"0\.[1-7]\.\d+", old_version):
            raise SystemExit(f"Unsupported migration version: {old_version}")
        now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        mode = state.get("delivery_mode", "standard")
        if mode not in ENABLED:
            raise SystemExit(f"Unknown delivery mode: {mode}")
        output = project / "AI/output"
        # 在修改任何现有文件前完成别名冲突检查。
        sources, originals = {}, {}
        roots = [output, delivery / "artifacts", delivery]
        for name, aliases in OLD_NAMES.items():
            candidates = list(dict.fromkeys(
                path.resolve() for root in roots for alias in [name, *aliases]
                if (path := root / alias).is_file()
            ))
            if candidates:
                if any(path.read_bytes() != candidates[0].read_bytes() for path in candidates[1:]):
                    raise SystemExit(f"Document naming conflict: {name}")
                sources[name] = candidates[0].read_text(encoding="utf-8")
                for path in candidates:
                    if not path.is_relative_to(project):
                        raise SystemExit(f"Source symlink escapes project: {path}")
                    originals[str(path.relative_to(project))] = path.read_bytes()
        old_phases = copy.deepcopy(state.get("phases", {}))
        phases = {}
        for phase in PHASES:
            previous = old_phases.get(phase)
            if phase == "development":
                previous = old_phases.get("development", old_phases.get("implementation"))
            phases[phase] = phase_record(previous, phase in ENABLED[mode])
        for phase in ("code_review", "testing"):
            if phase not in old_phases and old_phases.get("verification", {}).get("status", "not_started") not in {"not_started", "skipped"}:
                phases[phase].update(status="stale", note="旧合并验证不等同独立 CR 和测试证据")
        if phases["ui"]["status"] == "not_started" and "03 界面设计方案.md" not in sources:
            phases["ui"].update(status="skipped", required=False, note="尚无界面需求，后续按需启用")
        if "developer_self_test" not in old_phases:
            passed = bool(re.search(r"(?m)^status:\s*[\"']?passed", sources.get("06 开发自测报告.md", "")))
            if phases["development"]["status"] in {"complete", "approved"} and passed:
                phases["developer_self_test"].update(status="complete", note="沿用归档开发自测证据；非新一轮测试")
        old_release = old_phases.get("release", {})
        if old_release.get("status") not in {None, "not_started", "skipped"}:
            phases["release_preparation"].update(status="stale", required=old_release.get("required", True),
                                                note="旧发布检查不证明真实发布或放量完成，需复核")
        for phase in RELEASE_PHASES[1:]:
            phases[phase]["note"] = "不得由旧发布检查单推断实际发布完成"
        old_retro = old_phases.get("retrospective", {})
        if old_retro.get("status") not in {None, "not_started", "skipped"}:
            phases["effect_evaluation"].update(status="stale", required=old_retro.get("required", True),
                                              note="复核真实效果数据，旧复盘不是发布成功证据")
        state["legacy_phase_evidence"] = old_phases
        old_current = state.get("current_phase", "intake")
        state["current_phase"] = {"implementation": "development", "verification": "code_review",
                                  "release": "release_preparation", "retrospective": "effect_evaluation"}.get(old_current, old_current)
        if state["current_phase"] not in PHASES:
            state["current_phase"] = "intake"
        revision = state.get("revision", 0) + 1
        backup_name = f"{old_version}-to-{TEMPLATE_VERSION}-r{revision}"
        backup = delivery / "migrations" / backup_name
        if backup.exists():
            raise SystemExit(f"Backup already exists without pending transaction: {backup}")
        needed = {PHASE_FILES[phase] for phase, data in phases.items()
                  if data["status"] not in {"not_started", "skipped", "blocked"}}
        needed.add(WORKBENCH)
        new_names = set(PHASE_FILES.values()) - set(OLD_NAMES)
        for name in needed & new_names:
            if (output / name).exists():
                raise SystemExit(f"New-layout destination already exists: {output / name}")
        values = {"PROJECT_NAME": str(state.get("project_name", project.name)), "PROJECT_ROOT": str(project),
                  "DELIVERY_MODE": mode, "INTERACTION_MODE": state.get("interaction_mode", "guided"), "CREATED_AT": now}
        writes = {}
        for name in needed:
            if name in {"01 需求文档.md", "02 产品方案.md", "03 界面设计方案.md"} and name in sources:
                content = sources[name]
            else:
                content = render((core / "assets" / name).read_text(encoding="utf-8"), values)
                if name == WORKBENCH:
                    marker = "\n## 7. 交接记录"
                    before, after = content.split(marker, 1)
                    content = before
                    for heading, old_name in GROUPS[name]:
                        if old_name in sources:
                            content += f"\n\n## 迁移附录：{heading}\n\n" + body(sources[old_name]) + "\n"
                    # 保留全部历史交接行；旧模板的空 revision 0 行不覆盖真实历史。
                    rows = [line for line in sources.get("18 交接记录.md", "").splitlines()
                            if re.match(r"^\| \d+ \|", line)]
                    content += marker + "\n\n| Revision | 时间 | 宿主 | 模型 | 阶段 | 已完成 | 下一步 |\n|---|---|---|---|---|---|---|\n"
                    content += "\n".join(rows) + ("\n" if rows else "")
                else:
                    for heading, old_name in GROUPS.get(name, []):
                        if old_name in sources:
                            content += f"\n\n## 迁移附录：{heading}\n\n" + body(sources[old_name]) + "\n"
            if name == WORKBENCH:
                content += f"| {revision} | {now} | migration | unknown | {state['current_phase']} | 升级到 {TEMPLATE_VERSION}，合并文档并归档原文 | 复核当前阶段与真实证据 |\n"
            writes["AI/output/" + name] = content
        manifest = project / "AI/input/00 输入材料清单.md"
        if not manifest.exists():
            aliases = [project / "AI/input/source-manifest.md", project / "AI/input/输入材料清单.md",
                       delivery / "inputs/source-manifest.md"]
            found = [p for p in aliases if p.is_file()]
            writes["AI/input/00 输入材料清单.md"] = found[0].read_text(encoding="utf-8") if found else render(
                (core / "assets/00 输入材料清单.md").read_text(encoding="utf-8"), values)
        state.update(template_version=TEMPLATE_VERSION, schema_version=SCHEMA_VERSION, revision=revision,
                     phases=phases, artifact_layout="consolidated-lazy", artifact_overrides={},
                     last_updated=now, last_actor={"platform": "migration", "model": "unknown", "updated_at": now},
                     handoff={"summary": f"升级到 {TEMPLATE_VERSION}，原文归档至 {backup_name}",
                              "next_action": "复核合并文档，继续当前阶段"})
        state.setdefault("approvals", [])
        state.setdefault("open_questions", [])
        runtime = state.setdefault("runtime", {})
        runtime.setdefault("platform", "unknown")
        runtime.setdefault("model", "unknown")
        caps = runtime.setdefault("capabilities", {})
        for key in CAPABILITY_KEYS:
            caps.setdefault(key, "unknown")
        profile_path = delivery / "project-profile.yaml"
        profile = profile_path.read_text(encoding="utf-8") if profile_path.exists() else render(
            (core / "assets/project-profile.yaml").read_text(encoding="utf-8"), values)
        for key, value in (("template_version", TEMPLATE_VERSION), ("schema_version", SCHEMA_VERSION)):
            if re.search(rf"(?m)^{key}:", profile):
                profile = re.sub(rf"(?m)^{key}:.*$", f'{key}: "{value}"', profile)
            else:
                profile = f'{key}: "{value}"\n' + profile
        if "artifact_layout:" in profile:
            profile = re.sub(r"(?m)^\s+artifact_layout:.*$", '  artifact_layout: "consolidated-lazy"', profile)
        else:
            profile += '\ncompatibility:\n  artifact_layout: "consolidated-lazy"\n'
        if "lazy_artifacts:" not in profile:
            profile = profile.replace("delivery:\n", "delivery:\n  lazy_artifacts: true\n", 1)
        profile = re.sub(r"(?m)^(  current_phase:|updated_at:).*$",
                         lambda m: f'  current_phase: "{state["current_phase"]}"' if m[1].startswith(" ") else f'updated_at: "{now}"', profile)
        writes[".ai-delivery/project-profile.yaml"] = profile
        writes[".ai-delivery/state.json"] = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
        # 输出所有原文的独立快照和校验和，后续重新整理文档仍可追溯。
        backup.mkdir(parents=True)
        shutil.copy2(state_path, backup / "state.json")
        if profile_path.exists():
            shutil.copy2(profile_path, backup / "project-profile.yaml")
        archived = dict(originals)
        for path in output.glob("*.md"):
            archived.setdefault(str(path.relative_to(project)), path.read_bytes())
        hashes = {}
        for relative, data in archived.items():
            target = backup / "documents" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            hashes[relative] = hashlib.sha256(data).hexdigest()
        atomic_write(backup / "manifest.json", json.dumps(hashes, ensure_ascii=False, indent=2) + "\n")
        remove = {relative: hashlib.sha256(data).hexdigest() for relative, data in originals.items()
                  if relative not in writes}
        transaction = {"base_revision": revision - 1, "next_revision": revision,
                       "writes": writes, "remove": remove, "backup": str(backup.relative_to(project))}
        atomic_write(journal, json.dumps(transaction, ensure_ascii=False, indent=2) + "\n")
        recover(project, journal)
        print(f"Migrated to {TEMPLATE_VERSION}; backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
