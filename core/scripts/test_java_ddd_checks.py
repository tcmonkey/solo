#!/usr/bin/env python3
"""Forward-test Java DDD guardrails in disposable, independent Maven projects."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from install_java_ddd_checks import integrate


CORE = Path(__file__).resolve().parent.parent
INSTALLER = CORE / "scripts/install_java_ddd_checks.py"
APPLICATION = """package example.demo.application.demo.service;

import example.demo.application.demo.command.DemoCommand;
import example.demo.application.demo.result.DemoResult;
import example.demo.common.result.Result;

/**
 * 独立工程的公开入口校验样本。
 *
 * @author AIGenerator
 */
public class DemoApplication {
    /**
     * 查询并生成应用结果。
     *
     * @param demoCommand 查询命令
     * @return 统一应用结果
     *
     * @author AIGenerator
     */
    public Result<DemoResult> query(DemoCommand demoCommand) {
        // 1. 从命令取得业务标识并创建应用结果。
        DemoResult result = new DemoResult(demoCommand.id());
        return new Result<>(result);
    }
}
"""


class GuardrailTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="java-ddd-guardrails-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.write("pom.xml", """<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>example.demo</groupId>
    <artifactId>demo</artifactId>
    <version>1.0</version>
    <packaging>pom</packaging>
    <modules>
        <module>demo-application</module>
    </modules>
    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.13.0</version>
                <configuration>
                    <release>17</release>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
""")
        self.write("demo-application/pom.xml", """<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>example.demo</groupId>
        <artifactId>demo</artifactId>
        <version>1.0</version>
    </parent>
    <artifactId>demo-application</artifactId>
</project>
""")
        self.source = "demo-application/src/main/java/"
        self.application = self.source + "example/demo/application/demo/service/DemoApplication.java"
        self.write(self.application, APPLICATION)
        for folder, name, component in [
            ("application/demo/command", "DemoCommand", "String id"),
            ("application/demo/result", "DemoResult", "String id"),
            ("common/result", "Result<T>", "T data"),
        ]:
            generic = " * @param <T> 成功数据类型\n" if "<" in name else ""
            component_name = component.split()[-1]
            self.write(self.source + "example/demo/" + folder + "/" + name.split("<")[0] + ".java",
                       "package example.demo." + folder.replace("/", ".") + ";\n\n"
                       + "/**\n * 独立工程的稳定数据对象。\n *\n"
                       + generic + " * @param " + component_name + " 数据内容\n *\n"
                       + " * @author AIGenerator\n */\n"
                       + "public record " + name + "(" + component + ") {\n}\n")

    def write(self, name, content):
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def install(self):
        result = subprocess.run(
            ["python3", str(INSTALLER), "--project", str(self.root)],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def maven(self, *arguments):
        return subprocess.run(
            ["mvn", "-q", *arguments], cwd=self.root,
            capture_output=True, text=True, timeout=180,
        )

    def test_fresh_project_compiles_and_install_is_idempotent(self):
        self.install()
        before = (self.root / "pom.xml").read_bytes()
        self.install()
        self.assertEqual(before, (self.root / "pom.xml").read_bytes())
        self.assertEqual(
            (CORE / "assets/java-ddd/checkstyle.xml").read_bytes(),
            (self.root / "checkstyle.xml").read_bytes(),
        )
        self.assertTrue((self.root / "AI/output/19 Java DDD开发规范.md").is_file())
        result = self.maven("clean", "compile")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertTrue((self.root / "demo-application/target/classes").is_dir())

    def test_violations_stop_compile_before_javac(self):
        self.install()
        variants = {
            "NAM-APP-PARAM": APPLICATION.replace("demoCommand", "command"),
            "NAM-TYPE-PARAM": APPLICATION.replace("demoCommand", "wrongCommand"),
            "SIG-APP-OUTPUT": APPLICATION.replace("Result<DemoResult>", "Result<DemoCommand>"),
            "NAM-APP-ACTION": APPLICATION.replace(" query(", " execute("),
            "DOC-AUTHOR": APPLICATION.replace(" * @author AIGenerator\n", ""),
            "MissingJavadocMethod": APPLICATION.replace(
                APPLICATION[APPLICATION.index("    /**"):APPLICATION.index("    public Result")], ""
            ),
            "DI-FIELD": APPLICATION.replace(
                "public class DemoApplication {",
                "public class DemoApplication {\n"
                "    /**\n     * 注入违规样本。\n     *\n     * @author AIGenerator\n     */\n"
                "    @org.springframework.beans.factory.annotation.Autowired\n"
                "    private DemoCommand dependency;\n",
            ),
            "SQL-CUSTOM": APPLICATION.replace(
                "    public Result", '    @org.apache.ibatis.annotations.Select("select 1")\n    public Result'
            ),
        }
        for marker, source in variants.items():
            with self.subTest(rule=marker):
                self.write(self.application, source)
                result = self.maven("compile")
                output = result.stdout + result.stderr
                self.assertNotEqual(0, result.returncode, output)
                self.assertIn(marker, output)
                self.assertFalse((self.root / "demo-application/target/classes").exists())
        self.write(self.application, APPLICATION)
        result = self.maven("compile")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_implicit_public_interface_javadoc_is_enforced(self):
        self.install()
        name = self.source + "example/demo/common/api/DemoRepository.java"
        source = """package example.demo.common.api;

/**
 * 独立工程的接口契约校验样本。
 *
 * @author AIGenerator
 */
public interface DemoRepository {
    /**
     * 按标识查询内部数据。
     *
     * @param id 业务标识
     * @return 内部数据
     *
     * @author AIGenerator
     */
    String findById(String id);
}
"""
        method_doc = source[source.index("    /**"):source.index("    String findById")]
        variants = [
            ("MissingJavadocMethod", source.replace(method_doc, "")),
            ("JavadocMethod", source.replace("     * @param id 业务标识\n", "")),
            ("JavadocMethod", source.replace("     * @return 内部数据\n", "")),
            ("DOC-AUTHOR", source.replace("     * @author AIGenerator\n", "")),
        ]
        for index, (marker, variant) in enumerate(variants):
            with self.subTest(interface_violation=index):
                self.write(name, variant)
                result = self.maven("compile")
                output = result.stdout + result.stderr
                self.assertNotEqual(0, result.returncode, output)
                self.assertIn(marker, output)
                self.assertFalse((self.root / "demo-application/target/classes").exists())
        self.write(name, source)
        result = self.maven("compile")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_conflicting_file_is_preserved_without_partial_pom_write(self):
        self.write("checkstyle.xml", "<user-config/>\n")
        original = (self.root / "pom.xml").read_bytes()
        result = subprocess.run(
            ["python3", str(INSTALLER), "--project", str(self.root)],
            capture_output=True, text=True, timeout=30,
        )
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(original, (self.root / "pom.xml").read_bytes())
        self.assertEqual("<user-config/>\n", (self.root / "checkstyle.xml").read_text())
        self.assertFalse((self.root / "AI").exists())

    def test_pure_injection_constructors_and_fields_need_no_javadoc(self):
        self.install()
        # Local annotations test the AST scope, not Spring's runtime scanning.
        annotations = ["Component", "Service", "Repository", "Controller", "RestController",
                       "Configuration", "DomainService"]
        for annotation in annotations:
            self.write(self.source + "example/demo/common/" + annotation + ".java",
                       "package example.demo.common;\n\n/**\n * 扫描标记语法样本。\n *\n"
                       " * @author AIGenerator\n */\npublic @interface " + annotation + " {\n}\n")
            self.write(self.source + "example/demo/common/Demo" + annotation + ".java",
                       "package example.demo.common;\n\n/**\n * 纯依赖装配样本。\n *\n"
                       " * @author AIGenerator\n */\n@" + annotation + "\npublic class Demo" + annotation
                       + " {\n"
                       "    private final String dependency;\n\n    public Demo" + annotation
                       + "(String dependency) {\n        this.dependency = dependency;\n    }\n}\n")
        result = self.maven("clean", "compile")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        name = self.source + "example/demo/common/DemoComponent.java"
        valid = (self.root / name).read_text(encoding="utf-8")
        variants = {
            "validation": valid.replace("this.dependency = dependency;",
                                        'if (dependency == null) {\n'
                                        '            throw new IllegalArgumentException("dependency");\n'
                                        '        }\n        this.dependency = dependency;'),
            "initialization": valid.replace("this.dependency = dependency;",
                                            "this.dependency = dependency.trim();"),
            "unscanned": valid.replace("@Component\n", ""),
            "mutable_field": valid.replace("private final String", "private String"),
            "additional_assignment": valid.replace("this.dependency = dependency;",
                                                    "this.dependency = dependency;\n"
                                                    "        System.setProperty(\"demo\", dependency);"),
            "overloaded": valid.replace("\n}\n", "\n    public DemoComponent() {\n"
                                        "        this.dependency = null;\n    }\n}\n"),
        }
        for variant, source in variants.items():
            with self.subTest(constructor=variant):
                self.write(name, source)
                result = self.maven("validate")
                output = result.stdout + result.stderr
                self.assertNotEqual(0, result.returncode, output)
                self.assertIn("MissingJavadocMethod", output)
        # Exempt dependency fields only; do not hide business state or constants.
        for field in [
            '    private final String state = "ready";\n',
            '    private String state;\n',
            '    private static final String STATE = "ready";\n',
        ]:
            with self.subTest(undocumented_non_dependency=field):
                self.write(name, valid.replace("    private final String dependency;",
                                               field + "    private final String dependency;"))
                result = self.maven("validate")
                output = result.stdout + result.stderr
                self.assertNotEqual(0, result.returncode, output)
                self.assertIn("JavadocVariable", output)
        self.write(name, valid)
        result = self.maven("validate")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_diagnostics_are_readable_with_different_output_charsets(self):
        self.install()
        self.write(self.application, APPLICATION.replace("demoCommand", "wrongCommand"))
        expected = ("NAM-TYPE-PARAM: Request/Command parameter name must match its full type "
                    "in lowerCamelCase")
        for charset in ["UTF-8", "US-ASCII"]:
            with self.subTest(output_charset=charset):
                environment = os.environ.copy()
                environment["MAVEN_OPTS"] = environment.get("MAVEN_OPTS", "") + (
                    " -Dfile.encoding=" + charset + " -Duser.language=zh -Duser.country=CN"
                )
                result = subprocess.run(["mvn", "-q", "compile"], cwd=self.root, env=environment,
                                        capture_output=True, timeout=180)
                output = (result.stdout + result.stderr).decode("utf-8", errors="strict")
                self.assertNotEqual(0, result.returncode, output)
                self.assertIn(expected, output)
                diagnostic = next(line for line in output.splitlines() if expected in line)
                self.assertTrue(diagnostic.isascii(), diagnostic)
                self.assertFalse((self.root / "demo-application/target/classes").exists())
        self.write(self.application, APPLICATION)
        result = self.maven("compile")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_pom_shapes_and_existing_plugin_conflict(self):
        fragment = (CORE / "assets/java-ddd/maven-checkstyle-plugin.xml").read_text()
        original = (self.root / "pom.xml").read_text()
        without_build = original[:original.index("    <build>")] + "</project>\n"
        for shape in [original, without_build, original.replace("        <plugins>", "        <pluginManagement>\n            <plugins>")
                      .replace("        </plugins>", "            </plugins>\n        </pluginManagement>")]:
            installed = integrate(shape, fragment)
            self.assertEqual(installed, integrate(installed, fragment))
        conflict = integrate(original, fragment).replace("<failOnViolation>true", "<failOnViolation>false")
        with self.assertRaises(ValueError):
            integrate(conflict, fragment)


if __name__ == "__main__":
    unittest.main(verbosity=2)
