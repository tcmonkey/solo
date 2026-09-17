"""solo 交付阶段、文档映射和通用渲染规则。"""

from __future__ import annotations

import re
from pathlib import Path

TEMPLATE_VERSION = "0.8.0"
SCHEMA_VERSION = "1.5"
WORKBENCH = "00 交付工作台.md"
PHASE_LABELS = {
    "intake": "材料接收",
    "requirements": "需求",
    "product": "产品",
    "ui": "可选界面设计",
    "technical": "技术方案",
    "planning": "开发计划",
    "development": "编码",
    "developer_self_test": "开发自测",
    "code_review": "代码审查",
    "testing": "独立测试",
    "release_preparation": "发布准备",
    "initial_release": "初始发布",
    "observation": "发布中观测",
    "rollout": "分批放量",
    "full_release": "完整发布确认",
    "effect_evaluation": "效果评估与复盘",
}
PHASES = list(PHASE_LABELS)
RELEASE_PHASES = list(PHASE_LABELS)[10:15]
BASE_PHASES = {
    "intake", "requirements", "technical", "planning", "development",
    "developer_self_test", "code_review", "testing",
}
ENABLED = {
    "lite": BASE_PHASES,
    "standard": BASE_PHASES | {"product", *RELEASE_PHASES, "effect_evaluation"},
    "full": set(PHASES) - {"ui"},
}
PHASE_FILES = {
    "intake": WORKBENCH,
    "requirements": "01 需求文档.md",
    "product": "02 产品方案.md",
    "ui": "03 界面设计方案.md",
    "technical": "04 技术方案.md",
    "planning": "04 技术方案.md",
    "development": "05 开发交付记录.md",
    "developer_self_test": "05 开发交付记录.md",
    "code_review": "05 开发交付记录.md",
    "testing": "06 测试验收报告.md",
    **{phase: "07 发布运行记录.md" for phase in RELEASE_PHASES},
    "effect_evaluation": "08 效果评估与复盘.md",
}
VALID_STATES = {
    "not_started", "in_progress", "review", "approved",
    "skipped", "stale", "blocked", "complete",
}
CAPABILITY_KEYS = ("filesystem", "shell", "python", "repository", "browser", "persistence")
MODE_LABELS = {"lite": "简易", "standard": "平衡", "full": "完整"}
GOAL_LABELS = {
    "auto": "待确认",
    "plan_only": "方案想清楚", "development_ready": "功能可运行（自测和CR完成）",
    "release_ready": "上线前可验收（含发布准备）", "full_delivery": "上线交付闭环",
}
GOAL_ENDS = {"plan_only": "planning", "development_ready": "code_review",
             "release_ready": "release_preparation", "full_delivery": "effect_evaluation"}
STEPS = [
    ("01", "需求梳理", ("intake", "requirements")),
    ("02", "产品方案", ("product",)), ("03", "UI设计（按需）", ("ui",)),
    ("04", "技术方案与计划", ("technical", "planning")),
    *[(f"{index:02}", label, (phase,)) for index, label, phase in [
        (5, "编码开发", "development"), (6, "开发自测", "developer_self_test"),
        (7, "代码评审（CR）", "code_review"), (8, "独立测试", "testing"),
        (9, "发布准备", "release_preparation"), (10, "初始发布", "initial_release"),
        (11, "发布观测", "observation"), (12, "分批放量", "rollout"),
        (13, "完整发布确认", "full_release"), (14, "效果评估", "effect_evaluation"),
    ]],
]


def normalize_mode(value: str) -> str:
    mode = {label: key for key, label in MODE_LABELS.items()}.get(value, value.lower())
    if mode not in MODE_LABELS:
        raise ValueError(f"Unknown delivery mode: {value}")
    return mode


def normalize_goal(value: str) -> str:
    goal = {label: key for key, label in GOAL_LABELS.items()}.get(value, value)
    if goal not in GOAL_LABELS:
        raise ValueError(f"Unknown execution goal: {value}")
    return goal


def enabled_phases(mode: str, goal: str) -> set[str]:
    enabled = set(ENABLED[mode])
    if goal == "release_ready":
        enabled.add("release_preparation")
    elif goal == "full_delivery":
        enabled.update([*RELEASE_PHASES, "effect_evaluation"])
    return enabled


def route_plan(mode: str, goal: str = "auto", ui_required: bool = False, resume: bool = False) -> dict:
    """路线只是本次范围展示，不修改阶段历史或赋予执行权限。"""
    mode, goal = normalize_mode(mode), normalize_goal(goal)
    terminal = GOAL_ENDS.get(goal) or (None if resume else "code_review")
    end = PHASES.index(terminal) if terminal else len(PHASES) - 1
    enabled = enabled_phases(mode, goal)
    if ui_required:
        enabled.add("ui")
    selected, deferred, merged, optional = [], [], [], []
    for number, label, phases in STEPS:
        step = {"number": number, "label": label, "phases": list(phases)}
        if PHASES.index(phases[0]) > end:
            deferred.append(step)
        elif number == "02" and mode == "lite":
            merged.append({**step, "reason": "必要产品规则并入01需求"})
        elif number == "03" and not ui_required:
            optional.append({**step, "reason": "按界面需要启用，不默认生成UI"})
        elif any(phase in enabled for phase in phases):
            selected.append(step)
        else:
            optional.append({**step, "reason": "待实际发布范围确定后启用，模式不免除发布关口"})
    return {"mode": mode, "mode_label": MODE_LABELS[mode], "goal": goal,
            "goal_label": GOAL_LABELS[goal], "terminal_phase": terminal,
            "goal_is_recommendation": goal == "auto" and not resume,
            "selected": selected, "deferred": deferred, "merged": merged, "optional": optional}


def render(text: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def body(text: str) -> str:
    return re.sub(r"\A---\n.*?\n---\n", "", text, count=1, flags=re.S).strip()


def metadata(project: str, artifact: str, mode: str, now: str, status: str = "draft") -> str:
    import json
    return (
        "---\n"
        f"project: {json.dumps(project, ensure_ascii=False)}\n"
        f"artifact: {artifact}\nstatus: {status}\nversion: \"0.1\"\n"
        f"mode: \"{mode}\"\nupdated: \"{now}\"\nsources: []\n---\n\n"
    )


def ensure_project(project: Path, core: Path) -> None:
    if not project.is_dir():
        raise SystemExit(f"项目目录不存在：{project}")
    if project == core or core in project.parents:
        raise SystemExit("不能在技能资源目录中初始化或迁移业务项目")
