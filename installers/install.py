#!/usr/bin/env python3
"""构建、安装或更新 Solo；只迁移本工具管理的入口，不覆盖外来文件。"""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

from build_distributions import MARKER, PLATFORMS, ROOT, build, materialize, source_files, validate_managed


TARGETS = {"claude-code": Path(".claude/skills/solo"), "qwen-code": Path(".qwen/skills/solo")}
CODEX_TARGETS = {"agents": Path(".agents/skills/solo"), "codex": Path(".codex/skills/solo")}


def owned_link(target: Path, root: Path, platform: str) -> bool:
    """只承认当前工具包的已知新旧入口；失效旧链接也可识别。"""
    if not target.is_symlink():
        return False
    known = [root / "dist" / platform / "solo", root / "adapters" / platform / "solo",
             root / "adapters" / platform / "solo-delivery"]
    if platform == "codex":
        known.extend([root / "solo", root / "solo-delivery", root / "core"])
    return target.resolve(strict=False) in {path.resolve(strict=False) for path in known}


def target_for(platform: str, home: Path, codex_location: str) -> Path:
    if platform != "codex":
        return home / TARGETS[platform]
    # 自动模式统一使用官方用户级目录，不再根据 .codex 是否存在选择旧目录。
    return home / CODEX_TARGETS["agents" if codex_location == "auto" else codex_location]


def check_target(target: Path, root: Path, platform: str) -> None:
    if target.is_symlink():
        if not owned_link(target, root, platform):
            raise ValueError(f"Foreign symlink conflict: {target} -> {target.resolve(strict=False)}")
    elif target.exists():
        validate_managed(target, root, platform)


def cleanup_old_links(platform: str, home: Path, selected: Path, root: Path, dry_run: bool) -> None:
    relatives = list(CODEX_TARGETS.values()) if platform == "codex" else [TARGETS[platform]]
    candidates = [home / path.with_name("solo-delivery") for path in relatives]
    if platform == "codex":
        candidates.extend(home / path for path in relatives)
    for candidate in candidates:
        if candidate != selected and owned_link(candidate, root, platform):
            print(f"[{platform}] remove obsolete owned link: {candidate}")
            if not dry_run:
                candidate.unlink()


def install(platform: str, home: Path, root: Path = ROOT, dry_run: bool = False,
            codex_location: str = "auto", install_mode: str = "auto") -> bool:
    target = target_for(platform, home, codex_location)
    source = root / "dist" / platform / "solo"
    mode = ("symlink" if platform == "codex" else "copy") if install_mode == "auto" else install_mode
    try:
        check_target(target, root, platform)
        # 不为切换模式删除真实目录；调用者可继续使用当前已管理的副本。
        if target.exists() and not target.is_symlink() and mode == "symlink":
            raise ValueError(f"Existing managed copy: update with --install-mode copy: {target}")
        print(f"[{platform}] {'plan' if dry_run else 'install/update'} ({mode}): {target} <- {source}")
        if not dry_run:
            validate_managed(source, root, platform)
            target.parent.mkdir(parents=True, exist_ok=True)
            if mode == "symlink":
                # 临时链接 + replace，仅替换已验证属于本工具的链接或空目标。
                with tempfile.TemporaryDirectory(prefix=".solo-link-", dir=target.parent) as staging:
                    link = Path(staging) / "solo"
                    link.symlink_to(source.resolve(), target_is_directory=True)
                    os.replace(link, target)
            else:
                old_link = os.readlink(target) if target.is_symlink() else None
                files = {name: path for name, path in source_files(source).items() if name != MARKER}
                if old_link is not None:
                    target.unlink()
                try:
                    materialize(target, files, root, platform)
                except (OSError, ValueError):
                    if old_link is not None and not target.exists():
                        target.symlink_to(old_link, target_is_directory=True)
                    raise
        cleanup_old_links(platform, home, target, root, dry_run)
    except (OSError, ValueError) as error:
        print(f"[{platform}] conflict/error: {error}")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=("all", *PLATFORMS), default="all")
    parser.add_argument("--home", help="Alternative user home, for isolated testing")
    parser.add_argument("--dry-run", action="store_true", help="Plan only; do not build or write files")
    parser.add_argument("--codex-location", choices=("auto", *CODEX_TARGETS), default="auto")
    parser.add_argument("--install-mode", choices=("auto", "symlink", "copy"), default="auto",
                        help="auto: Codex directory symlink; other hosts real file copies")
    args = parser.parse_args()
    home = Path(args.home).expanduser().resolve() if args.home else Path.home()
    platforms = PLATFORMS if args.platform == "all" else (args.platform,)
    if not args.dry_run:
        # 先检查安装冲突，再构建；一个宿主的冲突不阻断其余宿主。
        eligible = []
        for platform in platforms:
            try:
                check_target(target_for(platform, home, args.codex_location), ROOT, platform)
                eligible.append(platform)
            except (OSError, ValueError) as error:
                print(f"[{platform}] conflict/error: {error}")
        if not eligible:
            return 1
        try:
            build(ROOT / "dist")
        except (OSError, ValueError) as error:
            print(f"Build failed: {error}")
            return 1
    else:
        eligible = list(platforms)
        print("Dry run: core + host configuration would be built; no files will be changed")
    results = [install(platform, home, dry_run=args.dry_run, codex_location=args.codex_location,
                       install_mode=args.install_mode) for platform in eligible]
    return 0 if len(eligible) == len(platforms) and all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
