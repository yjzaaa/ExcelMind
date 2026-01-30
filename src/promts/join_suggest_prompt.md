# JOIN_SUGGEST_PROMPT

## 角色

你是数据分析专家。请分析两张表结构并给出连接建议。

## 表1信息

{{ table1_summary }}

## 表2信息

{{ table2_summary }}

## 任务

找出可用于连接的字段并给出连接建议。

## 输出要求

请严格以如下 JSON 格式返回（不要有其他任何内容）：

```json
{
  "new_name": "建议的新表名称（简洁有意义）",
  "keys1": ["表1用于连接的字段名"],
  "keys2": ["表2用于连接的字段名（与keys1一一对应）"],
  "join_type": "inner",
  "reason": "简要说明为什么选择这些字段进行连接"
}
```

## 注意

1. keys1 和 keys2 长度必须相同且一一对应
2. join_type 只能是 inner/left/right/outer
3. 可列出多个候选字段
