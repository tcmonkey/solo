# WorkBuddy 宿主使用说明

先生成 WorkBuddy 导入包：

```bash
python3 /Users/monkey/Documents/kit/workspace/solo/installers/install.py --platform workbuddy
```

随后在 WorkBuddy 的「专家 · Skills · Connectors → Skills」中添加 Skill，导入：

```text
/Users/monkey/Documents/kit/workspace/solo/dist/workbuddy/solo-workbuddy.zip
```

导入包将 `SKILL.md` 放在 ZIP 根目录，并携带同一份 `references/`、`scripts/` 与 `assets/` 公共资源。安装后可在对话中调用 Solo；其交付状态仍写入目标业务项目的 `.ai-delivery/`、`AI/input/` 与 `AI/output/`，所以可与其他宿主顺序交接。

公共内容仅在 `core/` 维护。本适配器不复制 Solo 正文，只负责 WorkBuddy 的导入格式与使用说明。每次更新后重新生成 ZIP，并在 WorkBuddy 中导入更新版本。
