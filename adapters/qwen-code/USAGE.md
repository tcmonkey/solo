# Qwen Code 宿主使用说明

具备 Qwen Code 后安装：

```bash
python3 /Users/monkey/Documents/kit/workspace/solo/installers/install.py --platform qwen-code
```

在目标仓库启动 Qwen Code 并调用：

```text
/solo
```

不附加参数时，先展示完整14步及简易/平衡/完整模式，只问未知的项目目录和需求/附件；不要求先指定节点。理解需求后推荐模式和本次路线，默认guided，先确认需求范围。已有状态时展示进度和下一步，不重问已知信息。可用“先出方案”“功能可运行”“上线前可验收”“上线交付”表达终点，也可以不填。

也可打开 `/skills` 选择 solo。共享技能遵循 Qwen Code 当前项目指令，将机器状态持久保存于 `.ai-delivery/`，将中文名 Markdown 文档写入 `AI/output/`。

公共内容只在 core 维护。安装命令自动构建 dist/qwen-code/solo，再安装完整真实文件副本到 ~/.qwen/skills/solo；不依赖内部资源软链接。修改共享源后再次执行同一命令更新，已手工改动的安装文件会报告冲突并保留。

安装结构可通过回归测试；本次未检测到 Qwen Code 命令行程序，选择器及端到端执行尚未验证。
