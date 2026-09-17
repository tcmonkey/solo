#!/usr/bin/env python3
"""从共享内核与宿主配置构建完整 Skill；产物不包含内部软链接。"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PLATFORMS = ("codex", "claude-code", "qwen-code")
MARKER = ".solo-generated.json"
GENERATOR = "solo/installers"
EXCLUDED = {"__pycache__", ".git", ".idea", "target", ".DS_Store", ".flattened-pom.xml"}


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_files(directory: Path) -> dict[str, Path]:
    """只收集可分发文件，拒绝源目录中的资源链接。"""
    files = {}
    for path in sorted(directory.rglob("*")):
        relative = path.relative_to(directory)
        if EXCLUDED.intersection(relative.parts) or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise ValueError(f"Source resource must be a real file/directory: {path}")
        if path.is_file():
            files[relative.as_posix()] = path
    return files


def skill_files(root: Path, platform: str) -> dict[str, Path]:
    files = source_files(root / "core")
    # 使用说明属于工具包；目前仅 agents 是需要装入 Skill 的宿主配置。
    agents = root / "adapters" / platform / "agents"
    if agents.is_dir():
        files.update({"agents/" + name: path for name, path in source_files(agents).items()})
    if platform == "codex" and "agents/openai.yaml" not in files:
        raise ValueError("Missing Codex UI metadata: adapters/codex/agents/openai.yaml")
    for required in ("SKILL.md", "assets/state.json", "scripts/init_project.py"):
        if required not in files:
            raise ValueError(f"Missing required resource: {required}")
    return files


def fingerprints(directory: Path) -> dict[str, str]:
    """读取完整产物，不忽略未知文件；防止更新时覆盖用户改动。"""
    result = {}
    for path in sorted(directory.rglob("*")):
        relative = path.relative_to(directory)
        if "__pycache__" in relative.parts or path.suffix == ".pyc" or path.name == ".DS_Store":
            continue
        if path.is_symlink():
            raise ValueError(f"Generated skill contains a resource symlink: {path}")
        if path.is_file() and path.relative_to(directory).as_posix() != MARKER:
            result[path.relative_to(directory).as_posix()] = checksum(path)
    return result


def validate_managed(directory: Path, root: Path, platform: str) -> None:
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(f"Not a managed real directory: {directory}")
    marker = directory / MARKER
    if marker.is_symlink() or not marker.is_file():
        raise ValueError(f"Refusing to overwrite an unowned directory: {directory}")
    data = json.loads(marker.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid ownership marker: {directory}")
    if (data.get("generator"), data.get("source_root"), data.get("platform")) != (
        GENERATOR, str(root.resolve()), platform
    ):
        raise ValueError(f"Ownership marker mismatch: {directory}")
    if fingerprints(directory) != data.get("files"):
        raise ValueError(f"Generated files were modified; preserve/reconcile them first: {directory}")


def materialize(destination: Path, files: dict[str, Path], root: Path, platform: str) -> None:
    """先生成完整临时目录，再替换已验证归属及未被改动的旧产物。"""
    if destination.is_symlink():
        raise ValueError(f"Refusing a symlink build destination: {destination}")
    if destination.exists():
        validate_managed(destination, root, platform)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".solo-build-", dir=destination.parent))
    preserve_recovery = False
    try:
        stage = staging / "new"
        stage.mkdir()
        for relative, source in files.items():
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            target.chmod(0o755 if relative.startswith("scripts/") and source.suffix == ".py" else 0o644)
        metadata = {"generator": GENERATOR, "source_root": str(root.resolve()),
                    "platform": platform, "files": fingerprints(stage)}
        (stage / MARKER).write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        old = staging / "old"
        if destination.exists():
            destination.rename(old)
        try:
            stage.rename(destination)
        except OSError:
            if old.exists():
                try:
                    old.rename(destination)
                except OSError as error:
                    preserve_recovery = True
                    raise ValueError(f"Rollback failed; previous skill preserved at {old}: {error}") from error
            raise
    finally:
        # 回滚失败时保留旧目录供恢复；否则只清理本次生成的临时目录。
        if not preserve_recovery:
            shutil.rmtree(staging)


def build_zip(destination: Path, files: dict[str, Path]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".solo-zip-", dir=destination.parent) as staging:
        archive_path = Path(staging) / "solo.zip"
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for relative, path in files.items():
                info = zipfile.ZipInfo("solo/" + relative, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (0o755 if relative.startswith("scripts/") else 0o644) << 16
                archive.writestr(info, path.read_bytes())
        archive_path.replace(destination)


def build(output: Path, root: Path = ROOT) -> dict:
    output = output.expanduser().resolve()
    core = (root / "core").resolve()
    if output == root.resolve() or output == core or core in output.parents:
        raise ValueError("Build output must not overwrite the toolkit root or shared core")
    platform_files = {platform: skill_files(root, platform) for platform in PLATFORMS}
    if (output / "portable").is_symlink() or (output / "portable/solo.zip").is_symlink():
        raise ValueError("Refusing a symlink portable output")
    if (output / "manifest.json").is_symlink():
        raise ValueError("Refusing a symlink manifest output")
    # 在写入任何产物前检查所有已有目标，避免已知冲突造成部分更新。
    for platform in PLATFORMS:
        destination = output / platform / "solo"
        if destination.parent.is_symlink():
            raise ValueError(f"Refusing a symlink host output directory: {destination.parent}")
        if destination.exists() or destination.is_symlink():
            validate_managed(destination, root, platform)
    entries = {}
    for platform, files in platform_files.items():
        destination = output / platform / "solo"
        materialize(destination, files, root, platform)
        entries[platform] = {"path": str(destination.relative_to(output)), "files": fingerprints(destination)}
    portable = output / "portable/solo.zip"
    build_zip(portable, source_files(root / "core"))
    manifest = {
        "version": json.loads((core / "assets/state.json").read_text(encoding="utf-8"))["template_version"],
        "artifacts": {str(portable.relative_to(output)): checksum(portable)},
        "skills": entries,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(ROOT / "dist"), help="Distribution directory")
    args = parser.parse_args()
    try:
        manifest = build(Path(args.output))
    except (OSError, ValueError) as error:
        parser.exit(1, f"Build failed: {error}\n")
    print(f"Built {len(manifest['skills'])} host skills and portable/solo.zip")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
