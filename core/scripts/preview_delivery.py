#!/usr/bin/env python3
"""只读生成首次引导、建议路线或已有进度；不扫描工作区、不初始化或审批。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from delivery_model import (GOAL_LABELS, PHASE_LABELS, PHASES, STEPS, VALID_STATES, ensure_project,
                            normalize_goal, normalize_mode, route_plan)


MODE_OVERVIEW = [
    {"mode": "lite", "label": "简易", "path": "01 → 04 → 05 → 06 → 07 → 08",
     "detail": "小改动；02并入需求，04简短，08保留必要功能验收；实际上线时启用09～14"},
    {"mode": "standard", "label": "平衡", "path": "01 → 02 → 04 → 05 → 06 → 07 → 08",
     "detail": "常规功能；独立方案和测试，根据交付目标进入09～14"},
    {"mode": "full", "label": "完整", "path": "01 → 02 → 04 → 05 → 06 → 07 → 08 → 09～14",
     "detail": "新项目或高风险；强化性能、兼容、迁移和回滚；本次也可先停在方案"},
]
STATUS_LABELS = {"not_started": "未开始", "in_progress": "进行中", "review": "待评审",
                 "approved": "已确认", "complete": "已完成", "skipped": "已跳过/合并（见原因）",
                 "stale": "需重新验证", "blocked": "受阻", "unknown": "未知"}


def preview(project: Path | None = None, requirement: str = "", mode: str | None = None,
            goal: str | None = None, ui_required: bool = False) -> dict:
    data = {"kind": "collect_inputs", "missing_inputs": [], "steps": [
        {"number": number, "label": label, "phases": list(phases)} for number, label, phases in STEPS
    ], "modes": MODE_OVERVIEW, "goal_options": [
        {"goal": key, "label": label} for key, label in GOAL_LABELS.items() if key != "auto"
    ], "grants_production_authorization": False}
    if project is None:
        data["missing_inputs"].append("project")
    else:
        project = project.expanduser().resolve()
        ensure_project(project, Path(__file__).resolve().parent.parent)
        data["project"] = str(project)
        state_path = project / ".ai-delivery/state.json"
        if state_path.is_file():
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if not isinstance(state, dict):
                raise ValueError("Existing state must be an object; do not reinitialize")
            phases = state.get("phases", {})
            if not isinstance(phases, dict) or state.get("current_phase") not in PHASES:
                raise ValueError("Invalid existing state; inspect/recover it, do not reinitialize")
            if any(not isinstance(phases.get(phase), dict)
                   or phases[phase].get("status") not in VALID_STATES for phase in PHASES):
                raise ValueError("Incomplete/invalid phase history; inspect or migrate before continuing")
            actual_ui = phases.get("ui", {}).get("status") not in {None, "skipped"}
            plan = route_plan(mode or state.get("delivery_mode", "standard"),
                              goal or state.get("execution_goal", "auto"), ui_required or actual_ui, resume=True)
            end = PHASES.index(plan["terminal_phase"]) if plan["terminal_phase"] else len(PHASES) - 1
            pending = [phase for phase in PHASES[:end + 1] if phases.get(phase, {}).get("required")
                       and not (phases[phase].get("status") in {"approved", "complete"}
                                or (phases[phase].get("status") == "skipped" and phases[phase].get("note")))]
            # 历史中实际跳过的步骤按原状态显示，不被模式默认路线重新启用。
            for step in list(plan["selected"]):
                if all(phases.get(phase, {}).get("status") == "skipped" for phase in step["phases"]):
                    plan["selected"].remove(step)
                    plan["optional"].append({**step, "reason": "沿用历史跳过记录，请查工作台原因"})
            data.update(kind="resume", route=plan, revision=state.get("revision"),
                        current_phase=state["current_phase"],
                        progress=[{"number": number, "label": label, "statuses": {
                            phase: phases.get(phase, {}).get("status", "unknown") for phase in step_phases
                        }} for number, label, step_phases in STEPS],
                        next_phase=pending[0] if pending else None,
                        goal_reached=bool(plan["terminal_phase"]) and not pending
                        and phases[plan["terminal_phase"]].get("status") in {"approved", "complete"},
                        open_questions=state.get("open_questions", []),
                        handoff=state.get("handoff", {}))
            return data
    if not requirement.strip():
        data["missing_inputs"].append("requirement")
    if not data["missing_inputs"]:
        data["kind"] = "new_project"
    data["route"] = route_plan(mode or "standard", goal or "auto", ui_required)
    data["mode_is_provisional"] = mode is None
    return data


def describe(data: dict) -> str:
    lines = []
    plan = data["route"]
    if data["kind"] != "resume":
        lines.extend(["Solo 可以引导需求、方案、开发、测试和发布；不需要先了解节点名称。", "",
                      "完整步骤：" + " → ".join(step["number"] + " " + step["label"] for step in data["steps"]), "",
                      "| 模式 | 默认路径 | 适用与裁剪 |", "|---|---|---|"])
        lines.extend(f"| {item['label']} | {item['path']} | {item['detail']} |" for item in data["modes"])
        lines.append("\n03 UI在任意模式下按需加入；12可有理由不分批。流程编号不是文档序号。")
    else:
        lines.append(f"继续已有项目，Revision {data['revision']}；当前：{PHASE_LABELS[data['current_phase']]}。")
        lines.append("\n| 步骤 | 实际状态 |\n|---|---|")
        lines.extend(f"| {step['number']} {step['label']} | " + "; ".join(
            PHASE_LABELS[phase] + ": " + STATUS_LABELS.get(status, status)
            for phase, status in step["statuses"].items()) + " |"
                     for step in data["progress"])
    if data["missing_inputs"]:
        names = {"project": "项目目录", "requirement": "需求背景或附件"}
        lines.append("\n先提供：" + "、".join(names[key] for key in data["missing_inputs"]) + "。")
        lines.append("模式和终点都可不填，我会理解需求后推荐；先确认需求范围，不直接编码。")
        lines.append("可选成果：" + " / ".join(item["label"] for item in data["goal_options"]) + "。")
        example = (["项目：itineary"] if "project" in data["missing_inputs"] else [])
        example += (["需求：增加行程复制功能（也可提供附件）"] if "requirement" in data["missing_inputs"] else [])
        lines.append("最短回复示例：" + "；".join(example))
    else:
        provisional = "（暂定，待需求风险评估）" if data.get("mode_is_provisional") else ""
        lines.extend([f"\n模式：{plan['mode_label']}{provisional}；本次成果：{plan['goal_label']}。",
                      "本次路线：" + " → ".join(step["number"] + " " + step["label"] for step in plan["selected"])])
        for key, heading in (("merged", "合并"), ("optional", "按需/沿用记录"), ("deferred", "本次暂不执行")):
            if plan[key]:
                lines.append(heading + "：" + "；".join(step["number"] + " " + step["label"]
                             + ("（" + step["reason"] + "）" if "reason" in step else "（超过本次暂停位置）")
                             for step in plan[key]))
        if data["kind"] == "resume":
            if data["goal_reached"]:
                lines.append("状态记录显示已到达选定终点：核对产物证据后暂停并报告成果；继续需要新的范围决定。")
            elif data["next_phase"]:
                lines.append("建议下一步：" + PHASE_LABELS[data["next_phase"]] + "；按实际记录确认缺失材料。")
            else:
                lines.append("整体计划内没有未完成的必需阶段；核对工作台后报告成果。")
            if data["open_questions"]:
                lines.append("已有开放问题：" + json.dumps(data["open_questions"], ensure_ascii=False))
            if plan["goal"] == "auto":
                lines.append("已有项目未选择本次终点：沿用当前计划和交接，不擅自缩短到07。")
        else:
            if plan["goal_is_recommendation"]:
                lines.append("本次推荐做到功能可运行（至07），随需求范围一并确认；也可调整为先出方案等成果。")
            lines.append("下一步：展示需求理解、推荐依据和验收范围，等待范围确认。")
    lines.append("\n本预览未修改文件、未批准阶段，也未授权生产操作；进入阶段时会说明工作、所需材料和产物。")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path)
    parser.add_argument("--requirement", default="", help="已知背景或已接收附件的简要说明")
    parser.add_argument("--mode", type=normalize_mode, help="宿主根据需求推荐，可使用中文模式名")
    parser.add_argument("--goal", type=normalize_goal, help="可选成果终点")
    parser.add_argument("--ui-required", action="store_true")
    parser.add_argument("--json", action="store_true", help="输出结构化预览用于校验")
    args = parser.parse_args()
    try:
        data = preview(args.project, args.requirement, args.mode, args.goal, args.ui_required)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Preview failed; existing files preserved: {error}\n")
    print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else describe(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
