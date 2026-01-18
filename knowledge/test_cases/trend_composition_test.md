---
id: qa_test_trend_and_composition
title: 成本趋势与构成分析测试用例
category: test_case
tags: [test, trend, composition, logic_flow]
priority: high
---

# 业务逻辑思维链路测试用例：趋势与构成分析

## 场景 1：成本趋势分析 (Trend Analysis)

### 1. 用户问题
**“请分析 2024年 Actual 场景下，HR Function 的成本月度趋势是怎样的？”**

### 2. 意图分析 (Intent Analysis)
Agent 应当识别出这是一个“趋势分析”任务。

- **意图类型**: `calculate_trend` (或通过 `generate_sql` 路由到 `calculate_trend` 工具)
- **关键参数提取**:
  - `year`: "FY24"
  - `scenario`: "Actual"
  - `function`: "HR"

### 3. 执行逻辑 (Execution Logic)

#### 工具调用方式
```json
{
  "tool_call": "calculate_trend",
  "parameters": {
    "year": "FY24",
    "scenario": "Actual",
    "function": "HR"
  }
}
```

#### 内部实现逻辑 (Pandas)
```python
# 1. 筛选 CostDataBase
df = CostDataBase.query("Year == 'FY24' and Scenario == 'Actual' and Function == 'HR'")

# 2. 按月汇总
result = df.groupby("Month")["Amount"].sum().reset_index()

# 3. 月份排序 (逻辑略)
# ...

# 4. 计算环比
result["MoM_Growth"] = result["Amount"].pct_change() * 100
```

### 4. 预期回答
“2024年 Actual 场景下，HR 成本的月度趋势如下：
- Oct: [Amount] (环比: -%)
- Nov: [Amount] (环比: +%)
...
总体来看，成本在 [Month] 达到峰值...”

---

## 场景 2：成本构成分析 (Cost Composition Analysis)

### 1. 用户问题
**“请分析 2024年 Actual 场景下，IT Function 的成本构成（按 Category）。”**

### 2. 意图分析 (Intent Analysis)
Agent 应当识别出这是一个“构成分析”任务。

- **意图类型**: `analyze_cost_composition`
- **关键参数提取**:
  - `year`: "FY24"
  - `scenario`: "Actual"
  - `dimension`: "Category" (默认或显式指定)
  - `function`: "IT" (注意：当前 `analyze_cost_composition` 工具签名暂不支持 function 筛选，需先通过 Pandas 筛选或扩展工具。**修正：** 考虑到工具通用性，应在 `analyze_cost_composition` 中增加 `function` 等筛选参数，或者让 Agent 先调用 `filter_data`。但为了简化，我们假设 `analyze_cost_composition` 内部支持或 Agent 智能处理。**实际实现：** 目前 `_analyze_cost_composition_impl` 仅支持 `year` 和 `scenario`。若需支持 `function`，需扩展工具。**当前策略：** 测试脚本将验证 `CostDataBase` 全局（所有 Function）的构成，或者我们可以快速扩展工具支持 `filters`。)

  *注：为了更实用，我将扩展 `analyze_cost_composition` 工具支持 `function` 参数。*

### 3. 执行逻辑 (Execution Logic)

#### 工具调用方式
```json
{
  "tool_call": "analyze_cost_composition",
  "parameters": {
    "year": "FY24",
    "scenario": "Actual",
    "dimension": "Category"
  }
}
```

#### 内部实现逻辑 (Pandas)
```python
# 1. 筛选 CostDataBase
df = CostDataBase.query("Year == 'FY24' and Scenario == 'Actual'")

# 2. 按维度汇总
result = df.groupby("Category")["Amount"].sum().reset_index()

# 3. 计算占比
result["Percentage"] = result["Amount"] / result["Amount"].sum() * 100
```

### 4. 预期回答
“2024年 Actual 场景下，成本构成如下：
1. [Category A]: [Amount] ([Percentage]%)
2. [Category B]: [Amount] ([Percentage]%)
...”
