# 业务元数据与术语规范

> 业务表结构、字段规则与术语含义请集中维护在本文件。

## 数据源与表

## 业务元数据（机器可读 JSON）

```json
{
  "tables": {
    "cost": "SSME_FI_InsightBot_CostDataBase",
    "rate": "SSME_FI_InsightBot_Rate"
  },
  "default_tables": ["cost"],
  "intent_table_map": {
    "allocation": ["cost", "rate"],
    "general_query": ["cost"],
    "compare_budget_vs_actual": ["cost"],
    "trend": ["cost"]
  },
  "keyword_table_map": {
    "分摊": ["cost", "rate"],
    "allocation": ["cost", "rate"],
    "rate": ["rate"],
    "预算": ["cost"],
    "实际": ["cost"],
    "趋势": ["cost"],
    "对比": ["cost"]
  }
}
```

## 运行前配置（SQL Server）

- 表名不再通过环境变量注入，统一从本文件的 JSON 元数据解析
- 仅需配置 SQL Server 连接相关环境变量（主机、库、账号等）

## 字段与数值规则

- 字段与别名必须使用方括号，例如 [Cost text]
- [Amount] 必须 CAST([Amount] AS FLOAT)
- 参与计算/输出的字段使用 COALESCE(…, 0)
- [RateNo] 必须 REPLACE('%','') 后 CAST 为 FLOAT，再 /100
- 月度排序需使用 month_num 字段（或等价的月份序号列）

## 分摊优先级与联表

- 分摊优先使用 [CC]，仅在无 CC 时允许使用 [BL]
- 分摊场景联表条件(只在用户问题中包含多部门以及成本中心的情况下)：
  - cdb.[Year]=t7.[Year] AND cdb.[Scenario]=t7.[Scenario] AND cdb.[Key]=t7.[Key] AND cdb.[Month]=t7.[Month]
  - 联表类型优先 LEFT JOIN
- 非多部门分摊场景禁止联表，仅使用主表

## 意图识别规则

- 意图类型：allocation 或 general_query
- allocation 需提取：target_bl、year、scenario、function（function 必含 Allocation）
- 当问题同时出现 BL 与 CC 时，优先选择 CC

## 意图输出结构（建议）

- intent_type: allocation | general_query
- next_step: allocate_costs | generate_sql
- parameters:
  - target_bl
  - year
  - scenario
  - function
- reasoning
- field_mapping

## 术语与字段含义（示例）

- [Year]：财年
- [Scenario]：版本（Budget/Actual/Budget1）
- [Function]：职能部门
- [Cost text]：服务内容
- [Key]：分摊依据
- [Month]：月份
- [RateNo]：分摊比例
- [CC]：成本中心
- [BL]：业务线
