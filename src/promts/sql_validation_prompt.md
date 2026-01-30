# SQL_VALIDATION_PROMPT

## 角色

检查 SQL 是否符合规则。

## 数据结构

{{ columns_info }}

## 待验证代码

{{ sql_query }}

## 检查项

1. **只读**: 仅允许 SELECT（含 CTE），禁止 DDL/DML。
2. **字段与别名**: 所有字段与别名必须使用方括号包裹。
3. **语法规范**: 单语句、ORDER BY 仅用显式字段/别名、GROUP BY 完整。
4. **逻辑合理性**: 是否能回答用户问题？
5. **业务规则**: 表/字段/联表/分摊规则见 business/metadata.md。

## 输出格式

如果通过，请直接输出 "VALID"。
如果不通过，请输出 "INVALID: <具体错误原因>"。
