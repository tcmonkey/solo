# ZCode 宿主使用说明

以下相对路径均以 Solo 仓库根目录为准。先进入克隆或解压后的 Solo 目录，再安装：

```bash
cd <solo-repository-root>
python3 installers/install.py --platform zcode
```

安装器从共享 `core/` 构建 `dist/zcode/solo`，并将完整真实文件复制到当前用户的 `~/.zcode/skills/solo`。再次运行同一命令可更新；若安装目录含有手工改动，安装器会报告冲突并保留文件。公共技能内容只在 `core/` 维护。

在 ZCode 的「设置 → 技能」中点击「刷新」，确认 `solo` 已出现且处于启用状态。打开目标业务项目后，在 ZCode Agent 对话框输入：

```text
$solo 继续当前项目
```

也可在 `/` 菜单的「技能」分组选择 Solo。若在项目间切换宿主，先读取该业务项目的 `.ai-delivery/state.json` 与 `AI/output/00 交付工作台.md`，按当前修订号继续。

上述目录与调用方式依据 [ZCode 官方 Skill 文档](https://zcode.z.ai/cn/docs/skill)。安装结构可由仓库测试验证；ZCode 界面中的发现与完整交付流程仍需在 ZCode 内实测。
