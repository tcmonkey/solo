#!/usr/bin/env python3
"""Install local Solo adapters with safe filesystem symlinks."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCES = {
    "codex": ROOT / "solo",
    "claude-code": ROOT / "adapters/claude-code/solo",
    "qwen-code": ROOT / "adapters/qwen-code/solo",
}
TARGETS = {
    "claude-code": Path(".claude/skills/solo"),
    "qwen-code": Path(".qwen/skills/solo"),
}
CODEX_TARGETS = {
    "agents": Path(".agents/skills/solo"),
    "codex": Path(".codex/skills/solo"),
}


def legacy_targets(platform: str, home: Path) -> list[Path]:
    relatives = CODEX_TARGETS.values() if platform == "codex" else [TARGETS[platform]]
    return [home / relative.with_name("solo-delivery") for relative in relatives]


def remove_owned_legacy_links(platform: str, home: Path, source: Path, dry_run: bool) -> None:
    """Remove only old-name symlinks owned by this toolkit, never foreign installations."""
    old_source = SOURCES[platform].with_name("solo-delivery").resolve(strict=False)
    for old_target in legacy_targets(platform, home):
        if old_target.is_symlink() and old_target.resolve(strict=False) in {source, old_source}:
            print(f"[{platform}] remove renamed installation link: {old_target}")
            if not dry_run:
                old_target.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=["all", *SOURCES], default="all")
    parser.add_argument("--home", help="Override home directory, mainly for isolated testing")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--codex-location",
        choices=("auto", *CODEX_TARGETS),
        default="auto",
        help="Codex personal Skill location; auto preserves an existing installation",
    )
    return parser.parse_args()


def target_for(platform: str, home: Path, codex_location: str) -> Path:
    if platform != "codex":
        return home / TARGETS[platform]
    if codex_location != "auto":
        return home / CODEX_TARGETS[codex_location]
    for relative in CODEX_TARGETS.values():
        candidate = home / relative
        if candidate.exists() or candidate.is_symlink():
            return candidate
        legacy = candidate.with_name("solo-delivery")
        if legacy.exists() or legacy.is_symlink():
            return candidate
    if (home / ".agents/skills").is_dir():
        return home / CODEX_TARGETS["agents"]
    if (home / ".codex").is_dir():
        return home / CODEX_TARGETS["codex"]
    return home / CODEX_TARGETS["agents"]


def install(platform: str, home: Path, dry_run: bool, codex_location: str) -> bool:
    source = SOURCES[platform].resolve()
    target = target_for(platform, home, codex_location)
    if target.is_symlink():
        if target.resolve() == source:
            print(f"[{platform}] already installed: {target} -> {source}")
            remove_owned_legacy_links(platform, home, source, dry_run)
            return True
        print(f"[{platform}] conflict: {target} points to {target.resolve(strict=False)}")
        return False
    if target.exists():
        print(f"[{platform}] conflict: {target} already exists and is not a symlink")
        return False
    print(f"[{platform}] install: {target} -> {source}")
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source, target_is_directory=True)
    remove_owned_legacy_links(platform, home, source, dry_run)
    return True


def main() -> int:
    args = parse_args()
    home = Path(args.home).expanduser().resolve() if args.home else Path.home()
    platforms = list(SOURCES) if args.platform == "all" else [args.platform]
    results = [install(platform, home, args.dry_run, args.codex_location) for platform in platforms]
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
