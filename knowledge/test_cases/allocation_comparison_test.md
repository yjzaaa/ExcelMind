---
id: qa_test_allocation_comparison
title: 跨场景分摊结果对比测试用例
category: test_case
tags: [test, comparison, allocation, cross_scenario, logic_flow]
priority: high
---

# 业务逻辑思维链路测试用例：跨场景分摊对比

## 场景：预算分摊 vs 实际分摊 (混合维度对比)

### 1. 用户问题
**“26财年预算要分摊给413001的HR费用和25财年实际分摊给XP的HR费用相比，变化是怎么样的？”**

### 2. 意图分析 (Intent Analysis)
Agent 应当识别出这是一个复杂的“分摊结果对比”任务。

- **意图类型**: `compare_allocated_costs`
- **关键参数提取**:
  - **目标1**:
    - `target1`: "413001"
    - `target_type1`: "CC" (根据数字推断或明确上下文)
    - `year1`: "FY26"
    - `scenario1`: "Budget1" (预算)
  - **目标2**:
    - `target2`: "XP"
    - `target_type2`: "BL" (根据业务线名称推断)
    - `year2`: "FY25"
    - `scenario2`: "Actual" (实际)
  - **公共参数**:
    - `function`: "HR"

### 3. 执行逻辑 (Execution Logic)

#### 工具调用方式
```json
{
  "tool_call": "compare_allocated_costs",
  "parameters": {
    "target1": "413001",
    "target_type1": "CC",
    "year1": "FY26",
    "scenario1": "Budget1",
    "target2": "XP",
    "target_type2": "BL",
    "year2": "FY25",
    "scenario2": "Actual",
    "function": "HR"
  }
}
```

#### 内部实现逻辑 (Pandas)
```python
# 1. 计算 Target 1 (CC 413001 in FY26 Budget1)
# 筛选 CDB
cdb1 = CostDataBase.query("Year == 'FY26' and Scenario == 'Budget1' and Function == 'HR'")
# 筛选 T7 (CC)
t7_1 = Table7.query("Year == 'FY26' and Scenario == 'Budget1' and CC == 413001")
# 计算分摊
res1 = calculate_allocation(cdb1, t7_1)
amt1 = res1['Allocated_Amount'].sum()

# 2. 计算 Target 2 (BL XP in FY25 Actual)
# 筛选 CDB
cdb2 = CostDataBase.query("Year == 'FY25' and Scenario == 'Actual' and Function == 'HR'")
# 筛选 T7 (BL)
t7_2 = Table7.query("Year == 'FY25' and Scenario == 'Actual' and BL == 'XP'")
# 计算分摊
res2 = calculate_allocation(cdb2, t7_2)
amt2 = res2['Allocated_Amount'].sum()

# 3. 计算差异
diff = amt1 - amt2
pct = (diff / amt2 * 100)
```

### 4. 预期回答
“26财年 Budget1 分摊给 413001 的 HR 费用为 [Amount1]，25财年 Actual 分摊给 XP 的 HR 费用为 [Amount2]。
相比之下，变化金额为 [Difference]，变化幅度为 [Pct_Change]%。”
