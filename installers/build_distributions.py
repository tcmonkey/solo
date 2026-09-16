#!/usr/bin/env python3
"""Build a portable Agent Skill zip and its checksum manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "core"
TEMPLATE_VERSION = json.loads((CORE / "assets/state.json").read_text(encoding="utf-8"))["template_version"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(ROOT / "dist"), help="Distribution directory")
    return parser.parse_args()


def iter_core_files():
    for path in sorted(CORE.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and not path.name.endswith(".pyc"):
            yield path


def build_zip(destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in iter_core_files():
            relative = path.relative_to(CORE)
            info = zipfile.ZipInfo(str(Path("solo") / relative), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if path.parent.name == "scripts" else 0o644) << 16
            archive.writestr(info, path.read_bytes())


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    output = Path(parse_args().output).expanduser().resolve()
    portable = output / "portable/solo.zip"
    build_zip(portable)
    manifest = {
        "version": TEMPLATE_VERSION,
        "artifacts": {
            str(portable.relative_to(output)): checksum(portable),
        },
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Built portable skill: {portable}")
    print(f"Built manifest: {output / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
