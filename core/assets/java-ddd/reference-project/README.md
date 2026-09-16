# Java DDD 参考工程快照

这是 solo 技能随包携带的代码参考，不是完整生产脚手架，也不是另一份编码规范。当前规则源为 [Java DDD开发规范](../../../references/99%20Java%20DDD开发规范.md)；已有项目的明确约定和用户后续确认的变更优先。solo 0.8 的交付文档按需生成，阶段证据汇总于工作台，代码快照本身不变。

快照版本：1.2。基线来源：用户确认的 ddd 参考工程，提交 `7726493918a3e40cfd983e7424615a145d43c07f`。本版在已包含 start 显式装配清单的基线上同步用户确认的 revision/Flatten 调整，该调整尚未形成新的来源提交；源码、POM、资源、测试与根 Checkstyle 与当前参考工程对应文件一致。本说明与 .gitignore 为快照补充文件。

## 内容与选用

根 Maven 聚合工程包含 common、client、model、domain、application、infrastructure、adaptor、start 八个 ddd-* module。真实业务使用项目名作为 module 前缀，使用领域语言替换 Ddd 类名和 com.ddd 包名；不要把层级折叠为单个 src 下的目录。

start 的 POM 是本服务的显式装配清单：完整模板直接列出其余七个运行模块，依赖版本仍由根 POM 管理。真实业务按服务边界裁剪，不引入无用途、其他服务或仅工具用途的模块；测试专用依赖使用 test scope。清单声明不代表 start 承载业务逻辑，也不允许业务模块反向依赖 start。

所有链路共同参考 ddd-adaptor 的 DddController/DddInputAssembler 与 ddd-application 的 DddApplicationAssembler，关注 Request→Command→Param、DO→Application Result→Response 的分层转换。

| 场景 | Application 示例 | 重点继续阅读 |
|---|---|---|
| 写入 | DddWriteApplication | DddWriteDomainService、DddWriteParam、DddAggregate、DddEntity、DddRepositoryImpl：领域初始化/状态变更/完整聚合保存。 |
| 域内普通读 | DddReadApplication | DddRepository、DddRepositoryImpl：标识入参、聚合恢复及应用结果转换。 |
| 规则+计算 | DddRuleApplication | DddRuleDomainService、DddRuleRepositoryImpl、DddRuleAggregate、DddRuleEntity：加载规则后以模型行为计算。 |
| 纯计算 | DddCalculateApplication | DddCalculateDomainService、DddValue：无须虚构聚合或仓储。 |
| 外部普通读 | DddExternalReadApplication | application 的 DddOutputAdaptor 端口、adaptor 的 DddOutputAdaptorImpl/DddOutputConverter：Command→第三方请求→内部 DO。 |

结果和异常示例位于 ddd-common 与各模块 exception 包；PO/Mapper/基础仓储位于 ddd-infrastructure；启动、领域服务装配、Mapper 扫描、Logback 和数据库初始化位于 ddd-start。使用前按任务读取实际文件，不凭本索引假定业务正确。

## 生产适配边界

- H2/空密码/自动初始化 schema 只为本地运行；生产重新配置官方数据库驱动、凭据来源、迁移和约束，不能复制为生产连接。
- 外部响应是模拟结构，必须按真实方案接入调用、超时和错误映射。
- ddd_data 的 JSON 快照、ddd_rule 空表、幂等/版本示例需按实际模型评估；没有规则数据时规则相关入口返回失败是预期行为。
- 重新确认 JDK、Spring Boot、MyBatis-Plus 版本、鉴权、事务、并发、观测指标及回滚；日志中的 traceId 占位不代表已实现完整追踪。
- 真实需求只选所需链路和有用途的层，不复制全部演示接口、规则、表和测试断言。测试示例表达验证方法，不证明真实需求已验收。

## 验证与维护

Maven 3 项目版本只在根 POM 的 properties/revision 定义；根 version 和子模块 parent.version 使用 ${revision}，内部依赖版本仍由根以 ${project.version} 管理。升级只改 revision，或执行 `mvn clean package -Drevision=0.0.2-SNAPSHOT`。根 Flatten 插件继承到各模块，在 process-resources 生成版本已解析的发布 POM，install/deploy 使用该 POM；源码 POM 不变，clean 清除生成文件。生成的 .flattened-pom.xml 不入 Git 或快照；不为验证擅自发布到远程仓库。

将本目录复制或从发行包解压到临时工作目录，在聚合根执行 `mvn clean test`；不要在技能资产中运行构建，以免混入 target、缓存和日志。根 POM 的 validate 门禁默认检查主源码，不替代业务测试和架构审查。

本快照不包含 .git、.idea、target、.flattened-pom.xml、日志、AI 或 .ai-delivery。业务工程自己的 AI/input、AI/output 与 .ai-delivery 由 solo 流程初始化；本 README 是模板说明，生成真实项目时应另写该项目的 README，不直接复制其相对规范链接。

ddd 是独立的模板调试工程。它的修改经用户确认后才能更新此快照；同步规范/检查配置，更新来源提交及快照版本，并在临时副本验证、重新构建 solo.zip。不能从用户机器的绝对路径动态读取，不能自动把新业务项目代码反写成公共模板。
