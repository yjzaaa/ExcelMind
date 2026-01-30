# SQL_GENERATION_PROMPT

## 角色

生成可执行的 SQL Server 查询语句。

## ⚠️ SQL 生成准确率规则（全部集中在此）

1. **只输出 SQL**：仅输出单条 SELECT 语句（可含 CTE），不输出解释、不输出代码块、不输出 JSON。
2. **输出语法规范**：
   - 单语句原则：禁止多语句与分号拼接。
   - 字段与别名必须使用方括号包裹。
   - ORDER BY 只能使用 SELECT 里显式字段/别名。
   - 聚合查询 GROUP BY 必须包含所有非聚合字段。
3. **业务元数据**：业务表/字段/术语与分摊规则见 business/metadata.md。

## 数据上下文

{{ excel_summary }}

## 意图分析结果

{{ intent_analysis }}

## 用户问题

{{ user_query }}

## 错误修正（如果是重试）

{{ error_context }}

## 输出内容

只输出 SQL 语句。
