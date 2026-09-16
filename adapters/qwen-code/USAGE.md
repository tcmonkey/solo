# Qwen Code 宿主使用说明

具备 Qwen Code 后安装：

```bash
python3 /Users/monkey/Documents/kit/workspace/solo/installers/install.py --platform qwen-code
```

在目标仓库启动 Qwen Code 并调用：

```text
/solo
```

不附加参数时，新项目自动选择流程规模，使用 `guided` 模式；已有 `.ai-delivery/state.json` 的项目根据保存状态继续。已知需求或目标阶段可以追加在同一条消息中。

也可打开 `/skills` 选择 solo。共享技能遵循 Qwen Code 当前项目指令，将机器状态持久保存于 `.ai-delivery/`，将中文名 Markdown 文档写入 `AI/output/`。
