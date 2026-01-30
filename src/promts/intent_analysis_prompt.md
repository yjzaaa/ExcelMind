# INTENT_ANALYSIS_PROMPT

## 角色

识别意图并提取参数。

## 数据摘要

{{ excel_summary }}

## 用户问题

{{ user_query }}

## 任务

- 判断意图并提取参数（意图类型与参数规范见 business/metadata.md）。

## 输出要求

仅输出 JSON（不要 Markdown）：

```json
{
  "intent_type": "...",
  "next_step": "...",
  "parameters": {
    "key": "value"
  },
  "reasoning": "...",
  "field_mapping": {
    "字段名": "含义"
  }
}
```
