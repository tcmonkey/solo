# Codex 宿主使用说明

安装：

```bash
python3 /Users/monkey/Documents/kit/workspace/solo/installers/install.py --platform codex
```

在目标项目中调用：

```text
$solo
```

不附加参数时，先展示完整14步及简易/平衡/完整模式，只问未知的项目目录和需求/附件；不要求先指定节点。理解需求后推荐模式和本次路线，默认guided，先确认需求范围。已有状态时展示进度和下一步，不重问已知信息。可用“先出方案”“功能可运行”“上线前可验收”“上线交付”表达终点，也可以不填。

也可打开 `/skills` 选择 solo。公共内容只在 core 维护，Codex 元数据在 adapters/codex/agents/openai.yaml；安装命令自动生成 dist/codex/solo，并让 ~/.agents/skills/solo 链接到该完整目录。SKILL.md 与内部资源均为真实文件。

修改共享源后再次执行同一安装命令更新。自动迁移本工具的旧入口并清理重复旧链接，不覆盖其他来源的技能。生成 Markdown 使用中文文件名，存于业务项目 AI/output。

可执行 `python3 /Users/monkey/Documents/kit/workspace/solo/installers/verify_codex_discovery.py` 检查真实发现列表。本机已验证 solo 唯一、启用且展示元数据完整；输入框补全属于另外的界面验证，不能仅凭目录存在判定。
