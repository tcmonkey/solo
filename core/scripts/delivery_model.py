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
