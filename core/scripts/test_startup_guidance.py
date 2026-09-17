#!/usr/bin/env python3
"""在独立临时项目验证首次引导、模式/终点分离、进度恢复与只读边界。"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from delivery_model import PHASES, RELEASE_PHASES, STEPS, WORKBENCH, route_plan
from preview_delivery import preview


CORE = Path(__file__).resolve().parent.parent


class StartupGuidanceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="solo-startup-test-")
        self.project = Path(self.temp.name) / "business"
        self.project.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def run_script(self, name, *args, success=True):
        result = subprocess.run([sys.executable, "-B", str(CORE / "scripts" / name),
                                 "--project", str(self.project), *args], capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def initialize(self, *args):
        self.run_script("init_project.py", *args)
        return json.loads((self.project / ".ai-delivery/state.json").read_text())

    def save(self, state):
        (self.project / ".ai-delivery/state.json").write_text(json.dumps(state, ensure_ascii=False))

    def snapshot(self):
        return {str(path.relative_to(self.project)): path.read_bytes()
                for path in self.project.rglob("*") if path.is_file()}

    def test_first_bare_call_only_requires_project_and_requirement(self):
        before = self.snapshot()
        data = preview()
        self.assertEqual(data["missing_inputs"], ["project", "requirement"])
        self.assertEqual(len(data["steps"]), 14)
        self.assertEqual([item["label"] for item in data["modes"]], ["简易", "平衡", "完整"])
        self.assertTrue(data["mode_is_provisional"])
        self.assertEqual(data["route"]["goal"], "auto")
        self.assertEqual(before, self.snapshot())

    def test_known_inputs_not_reasked_and_new_recommendation_is_not_approval(self):
        self.assertEqual(preview(self.project)["missing_inputs"], ["requirement"])
        self.assertEqual(preview(requirement="已接收附件")["missing_inputs"], ["project"])
        data = preview(self.project, requirement="已接收需求附件")
        self.assertEqual(data["kind"], "new_project")
        self.assertEqual(data["missing_inputs"], [])
        self.assertTrue(data["route"]["goal_is_recommendation"])
        self.assertEqual(data["route"]["terminal_phase"], "code_review")
        self.assertFalse(data["grants_production_authorization"])
        self.assertFalse((self.project / ".ai-delivery").exists())

    def test_numbered_steps_cover_all_machine_phases_not_document_numbers(self):
        self.assertEqual([phase for _, _, phases in STEPS for phase in phases], PHASES)
        self.assertEqual(dict((number, phases) for number, _, phases in STEPS)["04"], ("technical", "planning"))

    def test_simple_change_merges_product_but_keeps_quality_stages(self):
        data = preview(self.project, "修复一个小问题", mode="简易", goal="release_ready")
        plan = data["route"]
        self.assertEqual([step["number"] for step in plan["selected"]], ["01", "04", "05", "06", "07", "08", "09"])
        self.assertEqual(plan["merged"][0]["number"], "02")
        self.assertEqual(plan["optional"][0]["number"], "03")

    def test_high_risk_full_mode_can_stop_at_plan_without_coding(self):
        plan = route_plan("完整", "plan_only")
        self.assertEqual([step["number"] for step in plan["selected"]], ["01", "02", "04"])
        self.assertEqual(plan["terminal_phase"], "planning")
        self.assertEqual(plan["deferred"][0]["number"], "05")

    def test_release_goal_enables_simple_release_but_never_authorizes_production(self):
        state = self.initialize("--mode", "简易", "--goal", "full_delivery")
        for phase in [*RELEASE_PHASES, "effect_evaluation"]:
            self.assertTrue(state["phases"][phase]["required"])
            self.assertEqual(state["phases"][phase]["status"], "not_started")
        self.assertEqual(state["approvals"], [])
        data = preview(self.project)
        self.assertFalse(data["grants_production_authorization"])
        self.assertEqual(data["route"]["terminal_phase"], "effect_evaluation")
        self.run_script("validate_delivery.py")

    def test_goal_does_not_mark_future_phases_complete_or_skipped(self):
        state = self.initialize("--mode", "full", "--goal", "plan_only")
        self.assertEqual(state["execution_goal"], "plan_only")
        for phase in PHASES[PHASES.index("development"):]:
            self.assertEqual(state["phases"][phase]["status"], "not_started")
        self.assertEqual({path.name for path in (self.project / "AI/output").iterdir()}, {WORKBENCH})
        self.run_script("validate_delivery.py")

    def test_existing_progress_goals_approvals_and_revision_are_preserved(self):
        state = self.initialize("--goal", "development_ready")
        for phase in PHASES[:PHASES.index("code_review") + 1]:
            if state["phases"][phase]["required"]:
                state["phases"][phase]["status"] = "complete"
        state["current_phase"] = "code_review"
        state["revision"] = 9
        state["approvals"] = [{"phase": "requirements", "approved_at": "previous"}]
        self.save(state)
        before = self.snapshot()
        data = preview(self.project)
        self.assertEqual(data["missing_inputs"], [])
        self.assertTrue(data["goal_reached"])
        self.assertEqual(data["revision"], 9)
        self.assertIsNone(data["next_phase"])
        self.assertEqual(before, self.snapshot())

    def test_old_state_without_goal_is_compatible_and_not_shortened(self):
        state = self.initialize()
        state.pop("execution_goal")
        self.save(state)
        profile = self.project / ".ai-delivery/project-profile.yaml"
        profile.write_text(profile.read_text().replace('  execution_goal: "auto"\n', ""))
        self.run_script("validate_delivery.py")
        before = self.snapshot()
        data = preview(self.project)
        self.assertIsNone(data["route"]["terminal_phase"])
        self.assertFalse(data["route"]["goal_is_recommendation"])
        self.assertEqual(before, self.snapshot())

    def test_goal_validation_and_profile_consistency(self):
        state = self.initialize()
        state["execution_goal"] = "unknown"
        self.save(state)
        self.run_script("validate_delivery.py", success=False)
        state["execution_goal"] = "plan_only"
        self.save(state)
        self.run_script("validate_delivery.py", success=False)
        profile = self.project / ".ai-delivery/project-profile.yaml"
        profile.write_text(profile.read_text().replace('execution_goal: "auto"', 'execution_goal: "plan_only"'))
        self.run_script("validate_delivery.py")

    def test_cli_preview_is_read_only_and_invalid_input_does_not_initialize(self):
        before = self.snapshot()
        result = self.run_script("preview_delivery.py", "--requirement", "行程复制", "--json")
        self.assertEqual(json.loads(result.stdout)["kind"], "new_project")
        self.run_script("init_project.py", "--goal", "unknown", success=False)
        self.assertEqual(before, self.snapshot())

    def test_ui_only_inserted_when_needed_and_future_testing_not_completed(self):
        data = preview(self.project, "增加页面", mode="standard", ui_required=True)
        self.assertIn("03", [step["number"] for step in data["route"]["selected"]])
        self.assertIn("08", [step["number"] for step in data["route"]["deferred"]])
        self.assertFalse(data["grants_production_authorization"])

    def test_invalid_existing_state_is_preserved(self):
        self.initialize()
        state_path = self.project / ".ai-delivery/state.json"
        state_path.write_text("null")
        before = self.snapshot()
        self.run_script("preview_delivery.py", success=False)
        self.assertEqual(before, self.snapshot())

    def test_required_skip_without_reason_is_not_goal_completion(self):
        state = self.initialize("--goal", "plan_only")
        for phase in PHASES[:PHASES.index("planning") + 1]:
            if state["phases"][phase]["required"]:
                state["phases"][phase]["status"] = "complete"
        state["phases"]["requirements"]["status"] = "skipped"
        self.save(state)
        data = preview(self.project)
        self.assertFalse(data["goal_reached"])
        self.assertEqual(data["next_phase"], "requirements")


if __name__ == "__main__":
    unittest.main(verbosity=2)
