#!/usr/bin/env python3
"""Install the approved Java DDD build guardrails without overwriting user configuration."""

from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path


def normalized(element: ET.Element):
    """Compare Maven elements independently of namespaces and whitespace."""
    return (
        element.tag.rsplit("}", 1)[-1],
        element.attrib,
        (element.text or "").strip(),
        tuple(normalized(child) for child in element),
    )


def integrate(pom: str, fragment: str) -> str:
    """Add an inherited validate/check execution to the root build/plugins."""
    root = ET.fromstring(pom)
    namespace = root.tag.split("}")[0] + "}" if "}" in root.tag else ""
    name = lambda tag: namespace + tag
    if root.findtext(name("packaging")) != "pom" or root.find(name("modules")) is None:
        raise ValueError("Java DDD template requires a Maven aggregation root with packaging=pom and modules")

    build = root.find(name("build"))
    plugins = build.find(name("plugins")) if build is not None else None
    expected = ET.fromstring(fragment)
    if plugins is not None:
        for plugin in plugins.findall(name("plugin")):
            if plugin.findtext(name("artifactId")) == "maven-checkstyle-plugin":
                if normalized(plugin) != normalized(expected):
                    raise ValueError("Existing Checkstyle plugin differs; reconcile it explicitly without overwriting")
                return pom

    rendered = "\n".join("            " + line for line in fragment.strip().splitlines())
    if build is None:
        block = "    <build>\n        <plugins>\n" + rendered + "\n        </plugins>\n    </build>\n"
        if not re.search(r"(?m)^</project>\s*$", pom):
            raise ValueError("Root POM needs a separate closing project line for safe insertion")
        return re.sub(r"(?m)^</project>", block + "</project>", pom, count=1)

    found = re.search(r"(?ms)^    <build>\s*\n.*?^    </build>", pom)
    if not found:
        raise ValueError("Format root build with four-space indentation before installing guardrails")
    section = found.group()
    if plugins is None:
        section = section.replace("    <build>\n", "    <build>\n        <plugins>\n" + rendered
                                  + "\n        </plugins>\n", 1)
    else:
        if not re.search(r"(?m)^        <plugins>\s*$", section):
            raise ValueError("Format direct build/plugins with eight-space indentation before installation")
        section = re.sub(r"(?m)^        <plugins>\s*$", "        <plugins>\n" + rendered, section, count=1)
    result = pom[:found.start()] + section + pom[found.end():]
    ET.fromstring(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Existing Java DDD Maven aggregation root")
    args = parser.parse_args()
    project = Path(args.project).expanduser().resolve()
    core = Path(__file__).resolve().parent.parent
    if project == core or core in project.parents:
        raise SystemExit("Refusing to install into the Skill resources")
    pom_path = project / "pom.xml"
    if not pom_path.is_file():
        raise SystemExit("Create the approved Maven root pom.xml before installing Java DDD checks")

    assets = core / "assets/java-ddd"
    fragment = (assets / "maven-checkstyle-plugin.xml").read_text(encoding="utf-8")
    original = pom_path.read_text(encoding="utf-8")
    try:
        updated = integrate(original, fragment)
    except (ValueError, ET.ParseError) as exception:
        raise SystemExit(str(exception)) from exception

    files = {
        project / "checkstyle.xml": (assets / "checkstyle.xml").read_text(encoding="utf-8"),
        project / "AI/output/19 Java DDD开发规范.md":
            (core / "references/Java DDD开发规范.md").read_text(encoding="utf-8"),
    }
    # Validate every target before making any write; preserve independently edited configuration.
    for path, content in files.items():
        if path.exists() and (not path.is_file() or path.read_text(encoding="utf-8") != content):
            raise SystemExit(f"Existing file differs; reconcile it explicitly without overwriting: {path}")

    for path, content in files.items():
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    if updated != original:
        pom_path.write_text(updated, encoding="utf-8")
    print(f"Java DDD guardrails installed: {project}")
    print("Run Maven from this aggregation root; validate/compile/test/package enforce Checkstyle")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
