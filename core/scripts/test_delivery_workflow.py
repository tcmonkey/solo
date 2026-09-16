#!/usr/bin/env python3
"""solo 0.8 初始化、阶段隔离、迁移与交接的结构回归测试。"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from delivery_model import PHASE_FILES, PHASES, TEMPLATE_VERSION, WORKBENCH, render

CORE = Path(__file__).resolve().parent.parent


class DeliveryWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="solo-workflow-")
        self.project = Path(self.temp.name) / "demo"
        self.project.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def run_script(self, name, *args, success=True):
        result = subprocess.run([sys.executable, str(CORE / "scripts" / name),
                                 "--project", str(self.project), *args], capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def state(self):
        return json.loads((self.project / ".ai-delivery/state.json").read_text())

    def save(self, state):
        (self.project / ".ai-delivery/state.json").write_text(json.dumps(state))

    def artifact(self, name):
        content = render((CORE / "assets" / name).read_text(), {
            "PROJECT_NAME": "demo", "DELIVERY_MODE": "standard", "CREATED_AT": "2026-09-16",
        })
        path = self.project / "AI/output" / name
        path.write_text(content)
        return path

    def initialize(self, mode="standard"):
        self.run_script("init_project.py", "--mode", mode)

    def legacy(self):
        self.initialize()
        state = self.state()
        state.update(template_version="0.7.0", schema_version="1.4", revision=44,
                     current_phase="code_review")
        state.pop("artifact_layout")
        state.pop("artifact_overrides")
        for name in list(state["phases"]):
            if name not in ["intake", "requirements", "product", "ui", "technical", "planning",
                            "development", "code_review", "testing"]:
                del state["phases"][name]
        for phase in ["intake", "requirements", "product", "technical", "planning", "development"]:
            state["phases"][phase]["status"] = "complete"
        state["phases"]["release"] = {"required": True, "status": "complete"}
        state["phases"]["retrospective"] = {"required": True, "status": "not_started"}
        state["approvals"] = [{"phase": "requirements", "source": "SRC-001", "approved_at": "old-time"}]
        self.save(state)
        (self.project / "AI/output" / WORKBENCH).unlink()
        for name in ["01 需求文档.md", "02 产品方案.md", "04 技术方案.md",
                     "05 开发计划.md", "06 开发自测报告.md", "07 代码审查报告.md",
                     "08 测试用例.md", "12 发布检查单.md", "18 交接记录.md"]:
            text = "---\nproject: demo\nartifact: 原文\nstatus: passed\nversion: 1\nupdated: old\n---\n\n# 历史记录\n"
            text += "原始证据 SRC-001\n"
            if name == "18 交接记录.md":
                text += "| 44 | old | codex | unknown | code_review | 自测完成 | 开始 CR |\n"
            (self.project / "AI/output" / name).write_text(text)
        return state

    def test_lazy_modes_and_non_overwrite(self):
        for mode in ["lite", "standard", "full"]:
            with self.subTest(mode=mode):
                if (self.project / ".ai-delivery").exists():
                    import shutil
                    shutil.rmtree(self.project / ".ai-delivery")
                    shutil.rmtree(self.project / "AI")
                self.initialize(mode)
                self.assertEqual({p.name for p in (self.project / "AI/output").iterdir()}, {WORKBENCH})
                self.assertEqual(self.state()["phases"]["ui"]["status"], "skipped")
                self.run_script("validate_delivery.py")
                before = (self.project / ".ai-delivery/state.json").read_bytes()
                self.run_script("init_project.py", success=False)
                self.assertEqual(before, (self.project / ".ai-delivery/state.json").read_bytes())

    def test_active_phase_requires_document(self):
        self.initialize()
        state = self.state()
        state["phases"]["requirements"]["status"] = "in_progress"
        self.save(state)
        result = self.run_script("validate_delivery.py", success=False)
        self.assertIn("Active artifact missing for requirements", result.stdout)
        self.artifact("01 需求文档.md")
        self.run_script("validate_delivery.py")

    def test_shared_document_does_not_complete_cr_or_testing(self):
        self.initialize()
        self.artifact("05 开发交付记录.md")
        state = self.state()
        state["phases"]["development"]["status"] = "complete"
        state["phases"]["developer_self_test"]["status"] = "complete"
        self.save(state)
        self.run_script("validate_delivery.py")
        self.assertEqual(self.state()["phases"]["code_review"]["status"], "not_started")
        state["phases"]["testing"]["status"] = "complete"
        self.save(state)
        self.artifact("06 测试验收报告.md")
        result = self.run_script("validate_delivery.py", success=False)
        self.assertIn("testing cannot complete before code_review", result.stdout)

    def test_override_is_local_and_merge_has_section(self):
        self.initialize()
        state = self.state()
        state["artifact_overrides"] = {"product": "../outside.md"}
        self.save(state)
        self.run_script("validate_delivery.py", success=False)
        state["artifact_overrides"] = {"product": "AI/output/01 需求文档.md"}
        state["phases"]["product"]["status"] = "in_progress"
        self.save(state)
        path = self.artifact("01 需求文档.md")
        self.run_script("validate_delivery.py", success=False)
        path.write_text(path.read_text() + "\n## 产品方案\n合并的实质方案\n")
        self.run_script("validate_delivery.py")

    def test_migration_preserves_history_and_no_false_release(self):
        previous = self.legacy()
        original = (self.project / "AI/output/06 开发自测报告.md").read_bytes()
        self.run_script("migrate_project.py")
        state = self.state()
        self.assertEqual(state["template_version"], TEMPLATE_VERSION)
        self.assertEqual(state["revision"], 45)
        self.assertEqual(state["approvals"], previous["approvals"])
        self.assertEqual(state["phases"]["developer_self_test"]["status"], "complete")
        self.assertEqual(state["phases"]["code_review"]["status"], "not_started")
        self.assertEqual(state["phases"]["initial_release"]["status"], "not_started")
        self.assertEqual(state["phases"]["full_release"]["status"], "not_started")
        self.assertEqual(state["phases"]["release_preparation"]["status"], "stale")
        self.assertFalse((self.project / "AI/output/06 测试验收报告.md").exists())
        archived = self.project / ".ai-delivery/migrations/0.7.0-to-0.8.0-r45"
        self.assertEqual((archived / "documents/AI/output/06 开发自测报告.md").read_bytes(), original)
        manifest = json.loads((archived / "manifest.json").read_text())
        self.assertEqual(manifest["AI/output/06 开发自测报告.md"], hashlib.sha256(original).hexdigest())
        self.run_script("validate_delivery.py")
        before = (self.project / ".ai-delivery/state.json").read_bytes()
        self.run_script("migrate_project.py")
        self.assertEqual(before, (self.project / ".ai-delivery/state.json").read_bytes())

    def test_migration_conflict_makes_no_existing_writes(self):
        self.legacy()
        target = self.artifact("05 开发交付记录.md")
        before = {p: p.read_bytes() for p in self.project.rglob("*") if p.is_file()}
        self.run_script("migrate_project.py", success=False)
        self.assertEqual(before, {p: p.read_bytes() for p in self.project.rglob("*") if p.is_file()})
        self.assertTrue(target.exists())

    def test_legacy_combined_verification_is_stale(self):
        self.legacy()
        state = self.state()
        state["template_version"] = "0.3.0"
        state["phases"].pop("code_review")
        state["phases"].pop("testing")
        state["phases"]["verification"] = {"required": True, "status": "complete"}
        self.save(state)
        self.run_script("migrate_project.py")
        self.assertEqual(self.state()["phases"]["code_review"]["status"], "stale")
        self.assertEqual(self.state()["phases"]["testing"]["status"], "stale")

    def test_handoff_revision_and_section(self):
        self.initialize()
        args = ["--platform", "codex", "--phase", "intake", "--summary", "材料接收",
                "--next-action", "确认范围", "--expected-revision"]
        self.run_script("record_handoff.py", *args, "99", success=False)
        self.assertEqual(self.state()["revision"], 0)
        path = self.project / "AI/output" / WORKBENCH
        path.write_text(path.read_text() + "\n## 8. 扩展材料\n保留内容\n")
        self.run_script("record_handoff.py", *args, "0")
        self.assertEqual(self.state()["revision"], 1)
        self.assertLess(path.read_text().index("| 1 |"), path.read_text().index("## 8. 扩展材料"))
        self.run_script("validate_delivery.py")

    def test_recoverable_handoff_transaction(self):
        self.initialize()
        from record_handoff import recover_transaction
        state_path = self.project / ".ai-delivery/state.json"
        path = self.project / "AI/output" / WORKBENCH
        journal = self.project / ".ai-delivery/.handoff-transaction.json"
        state = self.state()
        state["revision"] = 1
        content = path.read_text() + "| 1 | now | codex | unknown | intake | 恢复事务 | 确认范围 |\n"
        transaction = {"base_revision": 0, "next_revision": 1, "state": state, "handoff_content": content}
        journal.write_text(json.dumps(transaction))
        recover_transaction(journal, state_path, path)
        self.assertFalse(journal.exists())
        self.assertEqual(self.state()["revision"], 1)
        self.assertEqual(path.read_text(), content)
        self.run_script("validate_delivery.py")

    def test_recoverable_migration_and_revision_conflict(self):
        self.initialize()
        from migrate_project import recover
        journal = self.project / ".ai-delivery/.migration-transaction.json"
        path = self.project / "AI/output/01 需求文档.md"
        transaction = {"base_revision": 0, "next_revision": 1,
                       "writes": {"AI/output/01 需求文档.md": "事务恢复内容"}, "remove": {}}
        journal.write_text(json.dumps(transaction))
        recover(self.project, journal)
        self.assertEqual(path.read_text(), "事务恢复内容")
        journal.write_text(json.dumps(transaction))
        state = self.state()
        state["revision"] = 2
        self.save(state)
        with self.assertRaises(SystemExit):
            recover(self.project, journal)
        self.assertTrue(journal.exists())
        self.assertEqual(path.read_text(), "事务恢复内容")


if __name__ == "__main__":
    unittest.main(verbosity=2)
