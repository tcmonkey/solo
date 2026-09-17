#!/usr/bin/env python3
"""在临时目录验证单源构建、独立资源路径及安全安装/更新。"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from build_distributions import MARKER, PLATFORMS, ROOT, build, checksum, fingerprints, source_files
from install import install, target_for


class InstallationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="solo-install-test-")
        self.base = Path(self.temp.name)
        self.root = self.base / "toolkit"
        self.home = self.base / "home"
        for relative, source in source_files(ROOT / "core").items():
            target = self.root / "core" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        shutil.copytree(ROOT / "adapters/codex/agents", self.root / "adapters/codex/agents")
        self.output = self.root / "dist"

    def tearDown(self):
        self.temp.cleanup()

    def generate(self):
        return build(self.output, self.root)

    def host(self, platform):
        return self.output / platform / "solo"

    def test_real_files_and_platform_overlay(self):
        manifest = self.generate()
        common = source_files(self.root / "core")
        for platform in PLATFORMS:
            skill = self.host(platform)
            self.assertFalse(any(path.is_symlink() for path in skill.rglob("*")))
            self.assertEqual(manifest["skills"][platform]["files"], fingerprints(skill))
            for relative, source in common.items():
                self.assertEqual(checksum(source), checksum(skill / relative))
            self.assertEqual((skill / "agents/openai.yaml").exists(), platform == "codex")
            self.assertFalse((skill / "USAGE.md").exists())

    def test_portable_zip_matches_core_and_is_reproducible(self):
        first = self.generate()
        archive_path = self.output / "portable/solo.zip"
        with zipfile.ZipFile(archive_path) as archive:
            common = source_files(self.root / "core")
            self.assertEqual(set(archive.namelist()), {"solo/" + name for name in common})
            for name, path in common.items():
                self.assertEqual(archive.read("solo/" + name), path.read_bytes())
        self.assertEqual(first["artifacts"], self.generate()["artifacts"])

    def test_single_source_update_and_stale_file_removal(self):
        example = self.root / "core/references/temporary.md"
        example.write_text("old", encoding="utf-8")
        self.generate()
        example.unlink()
        skill_source = self.root / "core/SKILL.md"
        skill_source.write_text(skill_source.read_text(encoding="utf-8") + "\n更新示例\n", encoding="utf-8")
        self.generate()
        for platform in PLATFORMS:
            self.assertFalse((self.host(platform) / "references/temporary.md").exists())
            self.assertEqual(skill_source.read_bytes(), (self.host(platform) / "SKILL.md").read_bytes())

    def test_generated_edit_blocks_build_before_other_updates(self):
        self.generate()
        expected = (self.host("codex") / "SKILL.md").read_bytes()
        modified = self.host("qwen-code") / "SKILL.md"
        modified.write_text("user edits", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.generate()
        self.assertEqual(modified.read_text(), "user edits")
        self.assertEqual((self.host("codex") / "SKILL.md").read_bytes(), expected)

    def test_unowned_output_and_source_symlinks_rejected(self):
        foreign = self.host("codex")
        foreign.mkdir(parents=True)
        (foreign / "user.md").write_text("keep")
        with self.assertRaises(ValueError):
            self.generate()
        self.assertEqual((foreign / "user.md").read_text(), "keep")
        self.assertFalse(self.host("qwen-code").exists())
        (self.root / "core/references/link.md").symlink_to(self.root / "core/SKILL.md")
        with self.assertRaises(ValueError):
            source_files(self.root / "core")

    def test_old_links_migrate_and_codex_duplicate_removed(self):
        self.generate()
        for platform in PLATFORMS:
            target = target_for(platform, self.home, "auto")
            target.parent.mkdir(parents=True, exist_ok=True)
            old = self.root / ("solo" if platform == "codex" else "adapters/" + platform + "/solo")
            target.symlink_to(old, target_is_directory=True)
        duplicate = self.home / ".codex/skills/solo"
        duplicate.parent.mkdir(parents=True)
        duplicate.symlink_to(self.root / "solo", target_is_directory=True)
        for platform in PLATFORMS:
            self.assertTrue(install(platform, self.home, self.root))
            target = target_for(platform, self.home, "auto")
            self.assertEqual(target.is_symlink(), platform == "codex")
            self.assertTrue((target / "SKILL.md").is_file())
        self.assertFalse(duplicate.is_symlink())

    def test_renamed_owned_link_removed_but_foreign_legacy_kept(self):
        self.generate()
        old = self.home / ".claude/skills/solo-delivery"
        old.parent.mkdir(parents=True)
        old.symlink_to(self.root / "adapters/claude-code/solo-delivery")
        self.assertTrue(install("claude-code", self.home, self.root))
        self.assertFalse(old.is_symlink())
        old.symlink_to(self.base / "another-tool/solo")
        self.assertTrue(install("claude-code", self.home, self.root))
        self.assertTrue(old.is_symlink())

    def test_foreign_install_targets_preserved(self):
        self.generate()
        for platform in PLATFORMS:
            target = target_for(platform, self.home, "auto")
            target.mkdir(parents=True)
            (target / "user.md").write_text("keep")
            self.assertFalse(install(platform, self.home, self.root))
            self.assertEqual((target / "user.md").read_text(), "keep")
        other_home = self.base / "foreign-link-home"
        target = target_for("codex", other_home, "auto")
        target.parent.mkdir(parents=True)
        target.symlink_to(self.base / "foreign-skill")
        self.assertFalse(install("codex", other_home, self.root))
        self.assertEqual(target.readlink(), self.base / "foreign-skill")

    def test_copy_update_and_local_edit_protection(self):
        self.generate()
        self.assertTrue(install("claude-code", self.home, self.root))
        target = target_for("claude-code", self.home, "auto")
        source = self.root / "core/SKILL.md"
        source.write_text(source.read_text() + "\n新规则\n", encoding="utf-8")
        self.generate()
        self.assertNotEqual((target / "SKILL.md").read_bytes(), source.read_bytes())
        self.assertTrue(install("claude-code", self.home, self.root))
        self.assertEqual((target / "SKILL.md").read_bytes(), source.read_bytes())
        (target / "SKILL.md").write_text("local user edit")
        self.assertFalse(install("claude-code", self.home, self.root))
        self.assertEqual((target / "SKILL.md").read_text(), "local user edit")

    def test_detached_resources_and_python_cache_do_not_break_update(self):
        self.generate()
        detached = self.base / "detached-skill"
        shutil.copytree(self.host("qwen-code"), detached)
        # 完全脱离维护源后，初始化与检查脚本仍通过相对位置找到资源。
        self.root.rename(self.base / "source-hidden")
        project = self.base / "business"
        project.mkdir()
        for script in ("init_project.py", "validate_delivery.py"):
            result = subprocess.run([sys.executable, str(detached / "scripts" / script),
                                     "--project", str(project)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((project / "AI/output/00 交付工作台.md").is_file())
        (self.base / "source-hidden").rename(self.root)
        cache = self.host("codex") / "scripts/__pycache__"
        cache.mkdir()
        (cache / "demo.pyc").write_bytes(b"runtime cache")
        self.generate()
        self.assertFalse(cache.exists())

    def test_dry_run_and_codex_copy_mode(self):
        self.assertTrue(install("codex", self.home, self.root, dry_run=True))
        self.assertFalse(self.home.exists())
        self.assertFalse(self.output.exists())
        self.generate()
        self.assertTrue(install("codex", self.home, self.root, install_mode="copy"))
        target = target_for("codex", self.home, "auto")
        self.assertFalse(target.is_symlink())
        self.assertTrue(install("codex", self.home, self.root, install_mode="copy"))
        self.assertFalse(install("codex", self.home, self.root, install_mode="symlink"))
        self.assertTrue((target / MARKER).is_file())

    def test_cli_dry_run_writes_nothing(self):
        before = {name: checksum(path) for name, path in source_files(ROOT / "dist").items()}
        result = subprocess.run([sys.executable, str(ROOT / "installers/install.py"),
                                 "--platform", "all", "--home", str(self.home), "--dry-run"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.home.exists())
        after = {name: checksum(path) for name, path in source_files(ROOT / "dist").items()}
        self.assertEqual(before, after)

    def test_bad_marker_rejected(self):
        self.generate()
        marker = self.host("qwen-code") / MARKER
        marker.write_text("null")
        with self.assertRaises(ValueError):
            self.generate()

    def test_failed_replacement_restores_previous_skill(self):
        self.generate()
        expected = fingerprints(self.host("codex"))
        original = Path.rename

        def fail_new(path, target):
            if path.name == "new":
                raise OSError("simulated replacement failure")
            return original(path, target)

        with mock.patch.object(Path, "rename", fail_new), self.assertRaises(OSError):
            self.generate()
        self.assertEqual(fingerprints(self.host("codex")), expected)

    def test_failed_rollback_keeps_recovery_files(self):
        self.generate()
        expected = (self.host("codex") / "SKILL.md").read_bytes()
        original = Path.rename

        def fail_new_and_rollback(path, target):
            if path.name in {"new", "old"}:
                raise OSError("simulated replacement and rollback failure")
            return original(path, target)

        with mock.patch.object(Path, "rename", fail_new_and_rollback), self.assertRaises(ValueError):
            self.generate()
        recoveries = list((self.output / "codex").glob(".solo-build-*/old/SKILL.md"))
        self.assertEqual(len(recoveries), 1)
        self.assertEqual(recoveries[0].read_bytes(), expected)

    def test_output_directory_links_rejected_without_external_writes(self):
        self.output.mkdir()
        outside = self.base / "outside"
        outside.mkdir()
        (self.output / "codex").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.generate()
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
