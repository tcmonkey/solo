# solo 一人全栈开发技能

`solo` 是个人全栈一人开发的 Skill 工具包，支持从需求梳理到代码开发、审查与测试的持续交付，后续按真实使用需求优化其他宿主平台兼容性。它把机器状态保存在业务项目的 `.ai-delivery/`，把输入材料放在 `AI/input`，把需求、产品、技术、开发自测、代码审查、测试、发布和复盘等中文名 Markdown 文档放在 `AI/output`。

当前版本：`0.8.0`

入口、阶段规范和宿主使用说明统一采用中文。`SKILL.md` 等协议文件名、配置键、机器状态值、命令和代码标识符保持原样。安装器从共享源自动构建完整技能目录，不再依赖内部资源软链接；交付流程版本保持不变。

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
│   ├── codex/                    # USAGE.md + agents/openai.yaml
│   ├── claude-code/              # USAGE.md
│   └── qwen-code/                # USAGE.md
├── installers/                   # 构建、安装、更新与回归测试
├── dist/                         # 自动生成，不手工编辑
│   ├── codex/solo/               # 完整真实文件 + Codex 元数据
│   ├── claude-code/solo/         # 完整真实文件
│   ├── qwen-code/solo/           # 完整真实文件
│   └── portable/solo.zip         # 通用单目录发行包
├── START.md                      # 跨宿主使用参考
└── README.md
```

构建规则：`core 公共内容 + adapters/<宿主> 的专属配置 → dist/<宿主>/solo`。只在 core 维护公共流程、规范、模板和脚本；产物可重复生成，不属于多份维护源。adapters 下的 USAGE.md 不装入技能目录。

## 目录职责与目录改名

`solo` 是维护和分发工具包，不是一个需要整包加载的 Skill。

| 目录 | 作用 | 日常是否需要修改 |
|---|---|---|
| `core/` | 唯一维护源：流程入口、阶段规范、文档/检查模板及执行脚本。 | 优化流程与规范时修改这里。 |
| `adapters/` | 使用说明和实际专属配置；Codex 元数据在 adapters/codex/agents。 | 增加或调整宿主支持时修改。 |
| `installers/` | 构建完整目录并安装/更新；校验归属和文件完整性。 | 安装机制变化时修改。 |
| `dist/` | 完整技能目录、ZIP 与 SHA256 清单；不手工编辑。 | 由安装或构建命令生成。 |

普通 Skill 的 SKILL.md、references、assets、scripts 在每份产物中完整具备，内部全部是真实文件。额外目录服务于“跨宿主安装、单源维护、完整分发”，不要求 AI 每次读取整个工具包。references 是 AI 阅读的约束，assets 是生成到业务项目的模板，scripts 是初始化/迁移/校验/交接工具；业务代码与 AI/input、AI/output 不存放在此工具包里。

外层 solo 可以改名，技能名仍然是 solo，但 Codex 安装链接及生成归属标记记录了源路径。改名或移动前需规划迁移：新路径安装器不会把旧路径入口自动认作自己管理的入口。其他宿主的真实副本仍可读取，但更新时也需协调旧归属。脚本按自身位置寻找资源，完整产物或 ZIP 可独立使用，不依赖 core 所在位置；说明中的绝对路径示例和快捷命令也需同步修改。

旧名称 solo-delivery、旧 solo/solo 与 adapters 下的入口链接，可由安装器按已知目标安全迁移；只移除本工具管理的旧链接，不删除其指向的公共内容。其他来源的同名技能不会被覆盖或删除。

## 本地编码宿主安装

安装 Codex、Claude Code 和 Qwen Code 的个人 Skill 入口：

```bash
python3 /Users/monkey/Documents/kit/workspace/solo/installers/install.py --platform all
```

也可以通过 `--platform codex`、`--platform claude-code` 或 `--platform qwen-code` 单独安装。

| 宿主 | 默认个人位置 | 调用方式 |
|---|---|---|
| Codex | `~/.agents/skills/solo` → `dist/codex/solo`，一层目录链接 | `$solo` 或 `/skills` |
| Claude Code | `~/.claude/skills/solo`，完整真实文件副本 | `/solo` |
| Qwen Code | `~/.qwen/skills/solo`，完整真实文件副本 | `/solo` 或 `/skills` |

安装命令也是更新命令：自动构建后同步所选宿主。修改 core 或平台配置后必须重新执行安装，不再通过内部软链接即时生效。仅构建会更新 Codex 所链接的目录，但不会同步其他宿主的已安装副本，因此日常推荐安装命令。

Codex 自动模式统一选择官方用户级 .agents 路径，并移除本工具管理的另一处重复旧链接；`--codex-location codex` 保留为明确指定旧位置的选项。可用 `--install-mode copy` 安装 Codex 真实副本；已有副本更新时继续指定 copy，不自动删除目录切换为链接。其他宿主默认 copy，只有实际验证支持后才考虑 `--install-mode symlink`。

预览操作：`python3 installers/install.py --platform all --dry-run`，不构建、不写文件。外来目录、外来链接或被手工改动的生成文件会报告冲突并保留；一个宿主的安装冲突不阻断其他宿主。生成目录的 .solo-generated.json 保存归属和文件校验值，dist/manifest.json 保存发行清单；Python 缓存不进入发行包，也不被当作手工改动。

## 最短启动方式

先用对应宿主打开目标业务项目，然后选择 Skill：

```text
Codex：$solo
Claude Code：/solo
Qwen Code：/solo
```

裸调用的默认行为：

- 首次使用：展示完整步骤与中文模式，只问未知的项目目录和需求/附件；不强制填写模式或执行终点；
- 没有 `.ai-delivery`：理解需求后推荐简易、平衡或完整，使用 `guided`，从范围确认开始；
- 已有 `.ai-delivery`：展示真实进度和下一步，保留既有审批与终点，不重复启动问卷；
- 首轮停在需求范围确认，不直接开始产品设计或编码。

可以在同一条消息中追加最少信息：

```text
$solo
需求：开发会员等级和积分流水。
资料：@需求说明.pdf
```

### 完整步骤、模式和本次终点

01 需求梳理 → 02 产品方案 → 03 UI设计（按需）→ 04 技术方案与计划 → 05 编码开发 → 06 开发自测 → 07 代码评审（CR）→ 08 独立测试 → 09 发布准备 → 10 初始发布 → 11 发布观测 → 12 分批放量 → 13 完整发布确认 → 14 效果评估。

| 中文模式（内部标识） | 默认路径 | 特点 |
|---|---|---|
| 简易（lite） | 01 → 04 → 05 → 06 → 07 → 08 | 小改动；02并入需求，04简短，保留必要验收；实际上线时启用09～14 |
| 平衡（standard） | 01 → 02 → 04 → 05 → 06 → 07 → 08 | 常规功能；独立方案和测试，发布按交付目标进入 |
| 完整（full） | 01 → 02 → 04 → 05 → 06 → 07 → 08 → 09～14 | 新项目或高风险；强化专项，也可本次只先出方案 |

03始终按需，12可有理由不分批。步骤编号不是文档序号。模式决定详略，不免除质量和授权关口。

终点用成果表达：先把方案想清楚（至04）、功能可运行且自测/CR完成（至07）、上线前可验收并完成发布准备（至09）、上线交付闭环（至14）。终点可不填；新需求先推荐至07，在需求范围确认时一并确认。已有项目未记录终点时沿用原计划，不缩回07。暂不执行的整体必要步骤保留未开始或历史状态，不标完成或仅因暂停标skipped；上线意愿不等于生产授权。

理解需求后会展示推荐依据、本次编号路线、合并/按需/暂不执行原因及下一项决定。阶段开始说明要做什么、需要什么材料、生成什么产物。只读预览：`python3 core/scripts/preview_delivery.py`；可传 `--project /业务项目 --requirement '需求或附件摘要' --mode 平衡 --goal plan_only`。它不创建文件或批准阶段；无Python时仍按同样规则引导，不需要为了启动安装依赖。

新状态可选execution_goal与delivery_mode分别保存，旧0.8.0缺少终点字段仍兼容，不要求重建或迁移。回归：`python3 core/scripts/test_startup_guidance.py`，覆盖首次启动、已有进度、模式/终点、质量与只读边界；自然对话效果仍需真实调用检验。

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

该命令同时生成三个宿主的完整目录。新宿主只需增加实际差异配置及安装规则，不需要复制公共规范。

## 安装结构验证

```bash
python3 /Users/monkey/Documents/kit/workspace/solo/installers/test_installation.py
```

回归覆盖真实文件、清单/ZIP 校验、独立资源路径、安装/更新、旧链接迁移、冲突保护及 dry-run。结构测试不等于宿主行为测试：Codex 还需调用实际技能发现接口；Claude Code 和 Qwen Code 的选择器及端到端行为需在对应宿主中验证，未验证前不宣称已兼容。

Codex 发现检查：`python3 installers/verify_codex_discovery.py`。它只启动一个短生命周期的诊断 app-server，查询 skills/list，不启动模型任务、不修改配置、不结束桌面应用。2026-09-17 已用本机捆绑版本 codex-cli 0.154.0-alpha.6.2 验证：solo 唯一、启用、展示元数据完整、发现错误为空；这不代替输入框补全的界面验证。其他两个宿主当前仅验证构建与安装结构，本次未检测到其命令行程序。

同日回归结果：安装/迁移/冲突与故障恢复 16 项通过；交付流程 10 项在共享源及 Codex 产物中分别通过；Codex 产物的 Java DDD 门禁 7 项通过；三个宿主产物的 Skill 格式校验通过。已安装入口已迁移，重复旧 Codex 链接已移除；ddd 工程与公共规范、参考代码内容未改动。

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

技术方案草案生成后必须对整个方案做可行性反思与反例推演，发现矛盾回改正文并重新推演，区分推理、已执行实验和待验证条件；默认不估算人天/工时，实际排期由当事人决定。详见 [技术方案阶段规范](<core/references/05 技术方案阶段规范.md>)。

采用本工具 Java DDD 参考规范时，先阅读 [Java DDD开发规范](<core/references/99 Java DDD开发规范.md>)。开发阶段会为新 Maven 聚合工程安装根 `checkstyle.xml`、根 POM 的 validate 门禁和 `AI/output/19 Java DDD开发规范.md` 快照；无需逐个子模块配置。已有检查配置冲突时先融合，不直接覆盖。

已确认的参考代码快照位于 [reference-project](core/assets/java-ddd/reference-project/README.md)，包含八个 Maven module 的源码、POM、必要配置和测试，不包含 IDE/Git/构建产物或交付历史。开发计划按任务映射对应示例，编码阶段按需读取并生成真实业务逻辑；不自动复制全部演示链路。规范、参考代码与检查配置一并包含于 solo.zip。原 ddd 工程继续独立调试，用户确认后再更新公共快照。

可手动执行 `python3 core/scripts/install_java_ddd_checks.py --project /项目绝对路径`，再从项目聚合根执行 `mvn clean compile`。规范中区分自动校验和人工审查，编译通过不代表全部架构约束已验证。

Spring 项目中，纯注入构造器（DOC-005）及构造器注入的依赖字段（DOC-006）不写重复注释；业务字段、常量和日志字段仍保留说明，此约定不限于 ddd 示例；业务构造器、公开方法与接口契约继续保留多行中文 Javadoc。门禁消息使用英文 ASCII 和稳定规则 ID（MAV-007），不改变中文注释或业务错误信息；回归脚本 `python3 core/scripts/test_java_ddd_checks.py` 验证例外边界及不同输出编码。

## 模板迭代

项目经验先记录到该项目的 `AI/output/08 效果评估与复盘.md`。确认应成为公共规则后，再修改 `solo/core/` 并执行安装命令更新使用中的宿主。不要让单个项目自动改写公共模板。

## 历史工程边界修订（2026-09-17）

Java规范1.7：Controller、Application、DomainService及OutAdaptor实现主入口必须各自完整try-catch，禁止向上抛出、throws和catch重抛；事务完成/回滚后才转换结果，提交失败也必须捕获。默认Checkstyle新增ERR-BOUNDARY-CATCH/THROWS/RETHROW，错误语义与事务仍需专项验证。有前端时自动建立同级`<项目名>-app`独立项目；AI设计/接口/数据库说明与证据归AI/output，正式迁移、源码、测试和运行脚本保留构建位置。参考快照1.5同步当前ddd源码与新增失败回归。

## 当前业务代码质量约束（2026-09-18）

Java规范1.8：业务方法含私有辅助、回调按真实职责写中文编号步骤，实体持有初始化/校验/变化规则、聚合提供语义协作；迭代前后检查完整链路，复用职责并清理失效或重复代码。根validate默认执行Checkstyle及scripts/JavaBusinessQuality.java，后者扫描编号、45语句节点阈值与有限领域结构，不能证明注释含义或完整面向对象。独立CR和生产适配仍按流程执行。

参考快照1.6同步94个DDD来源文件、当前扫描器和有限回归。当前规范源为core/references/99 Java DDD开发规范.md，dist三个宿主与portable按同一源构建。

Java规范1.9修正实际编码遗漏的MAP边界和模块异常归属；QUALITY-MAPPING及QUALITY-ERROR-OWNER阻断有限DTO/异常构造位置反例，转换器还须逐点审查完整输入对象、真实默认值和失败分类。参考快照1.7同步规则缺失决策回领域及当前扫描器，不证明生产验收。

Java规范1.10明确公共技能面向所有适用项目，规则与版本日志不绑定具体应用或项目内SRC编号；具体改进来源与验证证据保留在所属项目。参考快照1.8仅更新说明，Java源码与门禁保持不变。
