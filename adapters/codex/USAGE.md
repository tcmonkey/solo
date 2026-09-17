# Codex 宿主使用说明

安装：

```bash
python3 /Users/monkey/Documents/kit/workspace/solo/installers/install.py --platform codex
```

在目标项目中调用：

```text
$solo
```

不附加参数时，新项目自动选择流程规模，使用 `guided` 模式；已有 `.ai-delivery/state.json` 的项目根据保存状态继续。已知需求或目标阶段可以追加在同一条消息中。

也可打开 `/skills` 选择 solo。公共内容只在 core 维护，Codex 元数据在 adapters/codex/agents/openai.yaml；安装命令自动生成 dist/codex/solo，并让 ~/.agents/skills/solo 链接到该完整目录。SKILL.md 与内部资源均为真实文件。

修改共享源后再次执行同一安装命令更新。自动迁移本工具的旧入口并清理重复旧链接，不覆盖其他来源的技能。生成 Markdown 使用中文文件名，存于业务项目 AI/output。

可执行 `python3 /Users/monkey/Documents/kit/workspace/solo/installers/verify_codex_discovery.py` 检查真实发现列表。本机已验证 solo 唯一、启用且展示元数据完整；输入框补全属于另外的界面验证，不能仅凭目录存在判定。
