# solo 一人全栈开发技能

`solo` 是个人全栈一人开发的 Skill 工具包，支持从需求梳理到代码开发、审查与测试的持续交付，后续按真实使用需求优化其他宿主平台兼容性。它把机器状态保存在业务项目的 `.ai-delivery/`，把输入材料放在 `AI/input`，把需求、产品、技术、开发自测、代码审查、测试、发布和复盘等中文名 Markdown 文档放在 `AI/output`。

当前版本：`0.8.0`

入口、阶段规范和宿主使用说明统一采用中文。`SKILL.md` 等协议文件名、配置键、机器状态值、命令和代码标识符保持原样，便于脚本及各宿主识别；宿主安装方式不变；本版收敛交付文档，并补齐发布观测、放量、完整确认与效果评估。

## 先区分宿主和模型

- **宿主平台**负责安装、发现和调用 Skill，并提供文件、终端、浏览器与代码仓库能力。当前维护 Codex、Claude Code、Qwen Code 三个宿主的适配入口；其他宿主后续按实际需求验证和适配。
- **模型提供方**负责理解和推理，例如 OpenAI、Claude、Qwen、DeepSeek、GLM 或 Doubao。模型名称不决定 Skill 的安装方式。

同一个模型放在不同宿主中，按宿主的调用方式使用。运行时会把宿主记录为 `platform`，把实际模型记录为 `model`。

## 架构

```text
solo/
├── core/                         # 唯一共享内核（Agent Skills 标准）
│   ├── SKILL.md
│   ├── references/               # 阶段规范与宿主能力规则
│   ├── assets/                   # 交付文档和状态模板
│   └── scripts/                  # 初始化、迁移、校验和交接
├── adapters/
│   ├── codex/                    # $solo
│   ├── claude-code/              # /solo
│   └── qwen-code/                # /solo
├── installers/
├── dist/                         # 可上传和分享的构建产物
├── START.md                      # 跨宿主使用参考
└── solo/                        # Codex UI 元数据与共享内核入口
```

平台适配器通过符号链接读取同一个 `core/`。修改公共流程、模板或脚本时只维护一份。

## 目录职责与目录改名

`solo` 是维护和分发工具包，不是一个需要整包加载的 Skill。

| 目录 | 作用 | 日常是否需要修改 |
|---|---|---|
| `core/` | 唯一维护源：流程入口、阶段规范、文档/检查模板及执行脚本。 | 优化流程与规范时修改这里。 |
| `solo/` | 实际 Skill 入口；共享内容链接到 core，agents 保存 Codex 展示和默认调用元数据。 | 一般不改；展示名称调整时修改 agents。 |
| `adapters/` | 各宿主的安装入口和使用说明；并非每个平台维护一套独立规范。 | 增加或调整宿主支持时修改。 |
| `installers/` | 本地安装及打包工具；安装通过用户级软链接让新项目发现 Skill。 | 安装机制或产物结构变化时修改。 |
| `dist/` | 生成的 solo.zip 与校验清单；可重新构建，不直接编辑。 | 分享或后续宿主适配时使用。 |

普通 Skill 的 SKILL.md、references、assets、scripts 已在 solo 入口中具备；额外目录服务于“跨宿主安装、单源维护、可上传打包”，不要求 AI 每次读取整个工具包。references 是给 AI 阅读的约束，assets 是生成到业务项目的模板，scripts 是执行初始化/迁移/校验/交接等任务的工具；业务代码与 AI/input、AI/output 不存放在此工具包里。

外层 solo 可以改名，技能名仍然是 solo，但当前用户级安装使用绝对路径软链接，外层改名会令已安装入口失效。需修复这些链接或先移除确认属于本工具包的失效安装链接，再从新路径执行安装器；安装器不会直接覆盖冲突链接。内部相对链接、按自身位置定位的脚本和已导出的 ZIP 不依赖外层文件夹名称；README/START/使用说明中的示例绝对路径和用户保存的快捷命令则需同步修改。

旧名称 solo-delivery 的本工具包安装链接会在执行安装器后自动迁移为 solo；其他来源的同名技能不会被删除。

## 本地编码宿主安装

安装 Codex、Claude Code 和 Qwen Code 的个人 Skill 入口：

```bash
python3 /Users/monkey/Documents/kit/workspace/solo/installers/install.py --platform all
```

也可以通过 `--platform codex`、`--platform claude-code` 或 `--platform qwen-code` 单独安装。

| 宿主 | 默认个人位置 | 调用方式 |
|---|---|---|
| Codex | 新安装优先 `~/.agents/skills/solo`；保留已有 `~/.codex/skills/solo` | `$solo` 或 `/skills` |
| Claude Code | `~/.claude/skills/solo` | `/solo` |
| Qwen Code | `~/.qwen/skills/solo` | `/solo` 或 `/skills` |

Codex 可通过 `--codex-location agents` 或 `--codex-location codex` 明确选择位置。安装器遇到已有非本工具管理的目录时会报告冲突，并继续检查其他平台，不会覆盖。

## 最短启动方式

先用对应宿主打开目标业务项目，然后选择 Skill：

```text
Codex：$solo
Claude Code：/solo
Qwen Code：/solo
```

裸调用的默认行为：

- 没有 `.ai-delivery`：自动判断 Lite、Standard 或 Full，使用 `guided`，从需求理解开始；
- 已有 `.ai-delivery`：读取最新状态和交接记录后继续；
- 缺少项目目录或需求：一次性询问必要输入；
- 首轮停在需求范围确认，不直接开始产品设计或编码。

可以在同一条消息中追加最少信息：

```text
$solo
需求：开发会员等级和积分流水。
资料：@需求说明.pdf
```

## 通用 Skill 发行包

构建供分享及后续宿主适配使用的 ZIP：

```bash
python3 /Users/monkey/Documents/kit/workspace/solo/installers/build_distributions.py
```

发行包：

```text
/Users/monkey/Documents/kit/workspace/solo/dist/portable/solo.zip
```

压缩包包含单一顶层 `solo/`，内部有 `SKILL.md`、规范、模板和脚本。它保留通用分发能力，但不意味着任意宿主都已验证兼容；接入新宿主前须确认安装协议、调用方式、工具能力和实际运行效果。当前不维护普通聊天模式 Playbook。

## 宿主能力与降级

Skill 在使用某项能力前检测并记录：

- 文件系统是否可写；
- Shell 与 Python 是否可用；
- 仓库是本地还是连接状态；
- 浏览器和持久存储是否可用。

有 Python 和可写项目时使用确定性脚本。只有文件能力时根据模板手动创建并做结构检查。不能持久化时返回可导出的状态与产物。不能执行编译、测试或代码审查时必须标记 `not_run`。

## 跨宿主继续同一项目

所有宿主以业务项目中的机器状态和中文交付文档为共同事实源：

```text
<业务项目>/
├── AI/
│   ├── input/
│   │   └── 00 输入材料清单.md
│   └── output/
│       ├── 00 交付工作台.md
│       ├── 01 需求文档.md
│       ├── 02 产品方案.md          # 小需求可并入需求
│       ├── 03 界面设计方案.md      # 可选
│       ├── 04 技术方案.md          # 默认内含计划
│       ├── 05 开发交付记录.md      # 编码、自测、CR 分节
│       ├── 06 测试验收报告.md      # 用例、结果、缺陷及专项
│       ├── 07 发布运行记录.md      # 分阶段发布与运行证据
│       └── 08 效果评估与复盘.md
└── .ai-delivery/
    ├── state.json
    └── project-profile.yaml
```

以上是完整路径的文档索引，不是初始化时全部生成的文件清单。

例如：

```text
Codex：$solo 完成需求文档并记录交接
Claude Code：/solo 继续，完善技术方案
Qwen Code：/solo 根据已批准方案开始编码
Codex：$solo 完成开发自测、代码审查和独立测试
```

状态变更会递增 `revision`。交接脚本使用 revision 检查、项目级写锁和待提交事务恢复，拒绝旧版本写入。仍不要让多个宿主同时编辑同一业务项目。

## 模型提供方

DeepSeek、GLM、Qwen、Doubao 等模型运行在 Claude Code 中时使用 Claude Code 适配器；运行在 Qwen Code 中时使用 Qwen Code 适配器。只有当模型厂商提供了新的宿主和不同安装协议时，才新增宿主适配器。

## 流程规模与按需文档

需求 → 产品 → 可选 UI → 技术与计划 → 编码 → 开发自测 → CR → 独立测试 → 发布准备 → 初始发布 → 观测 → 分批放量 → 完整发布确认 → 效果评估。

Lite 适合小改动，产品内容可并入需求；Standard 和 Full 保留完整发布、评估路径，UI 始终按需。实际需要发布的 Lite 项目也启用发布关口。一次性发布可以有理由不分批，但仍须观测和完整确认。

9 份主文档并非 9 个阶段：编码/自测/CR 共用开发交付记录，发布各阶段共用发布运行记录，但状态、证据和确认独立。初始化只生成工作台与输入清单；其余到相应阶段才生成，不铺开未来空文档。复杂任务和性能专项按需拆分，不重复维护。

[阶段规范与文档映射](<core/references/00 交付流程规范.md>)；references 用 00～10 排列流程规范，99 保存跨阶段的 Java DDD 约束。assets 根目录只放主模板，专项文档与 Java DDD 资源单独归类。

guided 在关键关口确认，continuous 在已授权范围持续。编写发布方案不意味着授权生产部署或放量。

## 手工命令

```bash
python3 /Users/monkey/Documents/kit/workspace/solo/core/scripts/init_project.py \
  --project /绝对路径/业务项目 --mode standard --interaction guided \
  --platform codex --model unknown \
  --capability filesystem=read-write --capability shell=available \
  --capability python=python3 --capability repository=local \
  --capability persistence=durable

python3 /Users/monkey/Documents/kit/workspace/solo/core/scripts/validate_delivery.py \
  --project /绝对路径/业务项目
```

已有 `0.1.x`～`0.7.x` 项目第一次使用 `0.8.0` 时执行：

```bash
python3 /Users/monkey/Documents/kit/workspace/solo/core/scripts/migrate_project.py \
  --project /绝对路径/业务项目
```

迁移先逐份归档旧文档、状态与配置，并保存 SHA256，再合并文档及同步机器状态。旧合并验证需要分离重评审；旧发布检查不证明已经部署、放量或商业效果达标。旧原文在 .ai-delivery/migrations 中可恢复。

## 开发、CR 与测试的边界

- 编码：按获批方案实现。
- 开发自测：构建、静态检查、单测、开发侧集成和最小冒烟；记录到开发交付记录。
- CR：检查实际差异的正确性、安全、数据、并发、兼容及可维护性；独立结论记录到同一文档。
- 独立测试：需求视角的功能、接口、边界、异常、回归，以及按需性能、兼容和回滚；用例、结果、缺陷统一写测试验收报告。
- 发布运行：准备、初始发布、带基线阈值窗口的观测、授权放量与完整确认；没有执行不能填写完成。

## Java DDD 编码规范与自动检查

采用本工具 Java DDD 参考规范时，先阅读 [Java DDD开发规范](<core/references/99 Java DDD开发规范.md>)。开发阶段会为新 Maven 聚合工程安装根 `checkstyle.xml`、根 POM 的 validate 门禁和 `AI/output/19 Java DDD开发规范.md` 快照；无需逐个子模块配置。已有检查配置冲突时先融合，不直接覆盖。

已确认的参考代码快照位于 [reference-project](core/assets/java-ddd/reference-project/README.md)，包含八个 Maven module 的源码、POM、必要配置和测试，不包含 IDE/Git/构建产物或交付历史。开发计划按任务映射对应示例，编码阶段按需读取并生成真实业务逻辑；不自动复制全部演示链路。规范、参考代码与检查配置一并包含于 solo.zip。原 ddd 工程继续独立调试，用户确认后再更新公共快照。

可手动执行 `python3 core/scripts/install_java_ddd_checks.py --project /项目绝对路径`，再从项目聚合根执行 `mvn clean compile`。规范中区分自动校验和人工审查，编译通过不代表全部架构约束已验证。

## 模板迭代

项目经验先记录到该项目的 `AI/output/08 效果评估与复盘.md`。确认应成为公共规则后，再修改 `solo/core/` 并重新构建发行包。不要让单个项目自动改写公共模板。
