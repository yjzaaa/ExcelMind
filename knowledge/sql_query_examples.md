---
id: kb_pandas_query_examples_001
title: Pandas查询与工具调用标准示例
category: query_pattern
tags:
  - Pandas
  - 复杂查询
  - 费用分摊
  - 预算对比
  - 工具调用
related_columns:
  - Year
  - Scenario
  - Function
  - Key
  - Cost text
  - RateNo
priority: high
---

# Pandas查询与工具调用标准示例

本文档提供了基于 `CostDataBase` (费用主表) 和 `Table7` (分摊规则表) 的常见业务问题处理范式。对于涉及多表关联、聚合计算或复杂逻辑的问题，**优先推荐使用专用工具**，其次是 `execute_pandas_query`。

## 1. 基础查询与筛选

### Q1: IT费用包括哪些服务？分摊依据是什么？
> **Question**: What services do IT cost include? And what is the allocation key?

*   **逻辑**: 从 `CostDataBase` 中筛选 Function 为 'IT' 的记录，并去重展示服务内容和分摊 Key。
*   **推荐 Tool**: `execute_pandas_query`
*   **Pandas Code**:
    ```python
    CostDataBase[CostDataBase['Function'] == 'IT'][['Cost text', 'Key']].drop_duplicates()
    ```

### Q2: FY26 计划了多少 HR 费用预算？
> **Question**: What was the HR Cost in FY26 BGT?

*   **逻辑**: 筛选 Year='FY26', Scenario='Budget1', Function='HR'，并汇总 'Year Total' (或 'Amount')。
*   **推荐 Tool**: `execute_pandas_query`
*   **Pandas Code**:
    ```python
    CostDataBase[
        (CostDataBase['Year'] == 'FY26') & 
        (CostDataBase['Scenario'] == 'Budget1') & 
        (CostDataBase['Function'] == 'HR')
    ]['Amount'].sum()
    ```

## 2. 复杂分摊计算 (跨表关联)

### Q3: FY25 实际分摊给 CT 的 IT 费用是多少？
> **Question**: What was the actual IT cost allocated to CT in FY25?

*   **逻辑**: 需要关联 `CostDataBase` 和 `Table7`。推荐使用封装好的分摊计算工具。
*   **推荐 Tool**: `calculate_allocated_costs`
*   **Tool Call**:
    ```json
    {
      "tool": "calculate_allocated_costs",
      "args": {
        "target": "CT",
        "target_type": "BL",
        "year": "FY25",
        "scenario": "Actual",
        "function": "IT Allocation"
      }
    }
    ```

### Q5: 分摊给 413001 的 HR 费用变化 (FY26 BGT vs FY25 Actual)
> **Question**: How is the change of HR allocation to 413001 between FY26 BGT and FY25 Actual?

*   **逻辑**: 涉及跨年、跨场景、针对特定 Cost Center (CC) 的分摊对比。
*   **推荐 Tool**: `compare_allocated_costs`
*   **Tool Call**:
    ```json
    {
      "tool": "compare_allocated_costs",
      "args": {
        "target1": "413001",
        "target_type1": "CC",
        "year1": "FY26",
        "scenario1": "Budget1",
        "target2": "413001",
        "target_type2": "CC", 
        "year2": "FY25",
        "scenario2": "Actual",
        "function": "HR Allocation"
      }
    }
    ```

## 3. 同比/环比分析与趋势

### Q4: 采购费用从 FY25 Actual 到 FY26 BGT 的变化？
> **Question**: How does Procurement Cost change from FY25 Actual to FY26 BGT?

*   **逻辑**: 对比两个场景的总金额。
*   **推荐 Tool**: `compare_scenarios`
*   **Tool Call**:
    ```json
    {
      "tool": "compare_scenarios",
      "args": {
        "year1": "FY26",
        "scenario1": "Budget1",
        "year2": "FY25",
        "scenario2": "Actual",
        "function": "Procurement"
      }
    }
    ```

### Q6: HR 费用的月度趋势如何？
> **Question**: What is the monthly trend of HR costs in FY24 Actual?

*   **逻辑**: 按月汇总并计算环比。
*   **推荐 Tool**: `calculate_trend`
*   **Tool Call**:
    ```json
    {
      "tool": "calculate_trend",
      "args": {
        "year": "FY24",
        "scenario": "Actual",
        "function": "HR"
      }
    }
    ```

## 4. 关键表字段对照

在编写 Pandas 查询时，请注意字段名大小写：

*   **CostDataBase**: `Year`, `Scenario`, `Function`, `Cost text`, `Key`, `Amount` (或 `Year Total`), `Month`
*   **Table7**: `Fiscal Year`, `Scenario`, `Key`, `CC`, `BL`, `RateNo` (或 `Value`), `Month`
