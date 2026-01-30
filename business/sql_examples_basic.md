# 基础查询与筛选类（示例库）

> 适用：枚举查询、单表聚合、明细 + 汇总。

## Q1：XX 费用包括哪些服务？分摊依据是什么？（枚举查询 + 去重）

**需求特征**：筛选指定 Function，枚举服务内容 [Cost text] 和分摊依据 [Key]，无计算 / 聚合，需 DISTINCT 去重。

**SQL 示例（单语句）**

```sql
SELECT DISTINCT
  [Cost text] AS [Service_Content],
  [Key] AS [Allocation_Key]
FROM SSME_FI_InsightBot_CostDataBase
WHERE [Function] = 'IT'
```

## Q2：FY26 计划了多少 HR 费用预算？（明细查询 + 汇总）

**需求特征**：筛选 Year/Scenario/Function，明细 + 汇总；汇总用 SUM(CAST([Amount] AS FLOAT))。

**SQL 示例（CTE + 单语句）**

```sql
WITH DetailedData AS (
  SELECT
    [Year],
    [Scenario],
    [Function],
    [Cost text] AS [Service_Content],
    [Key] AS [Allocation_Key],
    [Month],
    COALESCE(CAST([Amount] AS FLOAT), 0.0) AS [Amount]
  FROM SSME_FI_InsightBot_CostDataBase
  WHERE [Year] = 'FY26' AND [Scenario] = 'Budget1' AND [Function] = 'HR'
),
AggregatedData AS (
  SELECT
    [Year],
    [Scenario],
    [Function],
    SUM(COALESCE(CAST([Amount] AS FLOAT), 0.0)) AS [Total_HR_Cost_FY26_Budget1]
  FROM SSME_FI_InsightBot_CostDataBase
  WHERE [Year] = 'FY26' AND [Scenario] = 'Budget1' AND [Function] = 'HR'
  GROUP BY [Year], [Scenario], [Function]
)
SELECT * FROM DetailedData
UNION ALL
SELECT [Year], [Scenario], [Function], NULL, NULL, NULL, [Total_HR_Cost_FY26_Budget1]
FROM AggregatedData
ORDER BY [Year] DESC, [Scenario], [Function];
```
