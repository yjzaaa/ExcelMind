# RESULT_REVIEW_PROMPT

## 角色

检查 SQL 执行结果是否足以回答问题。

## 用户问题

{{ user_query }}

## 执行 SQL

{{ sql_query }}

## 执行结果

{{ execution_result }}

## 规则

- 若结果为空、明显缺失关键对比项或无法支撑问题结论，判定为 RETRY，并给出原因。
- 若结果可回答问题，判定为 PASS。
- 只输出一行：
  - PASS
  - RETRY: <原因>
