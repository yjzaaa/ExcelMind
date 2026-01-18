---
id: qa_test_scenario_comparison
title: 跨场景对比分析测试用例
category: test_case
tags: [test, comparison, budget_vs_actual, logic_flow]
priority: high
---

# 业务逻辑思维链路测试用例：跨场景对比

## 场景：预算与实际对比 (Budget vs Actual)

### 1. 用户问题
**“26财年采购的预算费用和25财年实际数比，变化是什么？”**

### 2. 意图分析 (Intent Analysis)
Agent 应当识别出这是一个“跨场景对比”任务。

- **意图类型**: `compare_scenarios`
- **关键参数提取**:
  - `year1`: "FY26" (26财年)
  - `scenario1`: "Budget1" (预算)
  - `year2`: "FY25" (25财年)
  - `scenario2`: "Actual" (实际数)
  - `function`: "Procurement" (采购)

### 3. 执行逻辑 (Execution Logic)

#### 工具调用方式
```json
{
  "tool_call": "compare_scenarios",
  "parameters": {
    "year1": "FY26",
    "scenario1": "Budget1",
    "year2": "FY25",
    "scenario2": "Actual",
    "function": "Procurement"
  }
}
```

#### 内部实现逻辑 (Pandas)
```python
# 1. 计算 Target Amount
amt1 = CostDataBase.query("Year == 'FY26' and Scenario == 'Budget1' and Function == 'Procurement'")["Amount"].sum()

# 2. 计算 Base Amount
amt2 = CostDataBase.query("Year == 'FY25' and Scenario == 'Actual' and Function == 'Procurement'")["Amount"].sum()

# 3. 计算差异
diff = amt1 - amt2
pct = (diff / amt2 * 100)
```

### 4. 预期回答
“26财年采购预算 (Budget1) 为 [Amount1]，25财年实际数 (Actual) 为 [Amount2]。
相比之下，变化金额为 [Difference]，变化幅度为 [Pct_Change]%。”
