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

也可打开 `/skills` 选择 solo。Codex 展示元数据位于工具包的 `solo/agents/openai.yaml`；全部流程内容链接至共享 `core/`，生成 Markdown 使用中文文件名，存于 `AI/output/`。
