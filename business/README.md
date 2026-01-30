# SQL 示例库与模板（业务文件）

此目录用于维护“问题 → 生成 SQL 示例 → 生成模板”的业务文档，便于业务规范独立演进与复用。

## 目录结构

- sql_examples_basic.md：基础查询与筛选
- sql_examples_allocation.md：分摊计算（跨表关联）
- sql_examples_trend.md：对比 / 趋势分析
- sql_generator_template.md：分摊 SQL 生成器模板（Python）
- metadata.md：业务表/字段/术语规范

## 使用方式

这些文件用于业务规范沉淀与模板复用，提示词仅保留通用规则。

## SQL Server 配置提示

- 表名从 business/metadata.md 的 JSON 元数据解析
- 仅需配置 SQL Server 连接相关环境变量（主机、库、账号等）
