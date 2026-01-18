---
id: qa_test_allocation_logic
title: IT 费用分摊计算测试用例
category: test_case
tags: [test, allocation, logic_flow]
priority: high
---

# 业务逻辑思维链路测试用例

## 1. 用户问题
**“请计算 2024年 Scenario1 下，Consumer Banking (CB) 业务线分摊到的 IT Allocation 费用是多少？”**

## 2. 意图分析 (Intent Analysis)
Agent 应当识别出这是一个复杂的“分摊计算”任务，而不是简单的 SQL 查询。

- **意图类型**: `allocate_costs` (或通过 `generate_sql` 路由到 `allocate_costs` 工具)
- **关键参数提取**:
  - `target_bl`: "CB" (Consumer Banking)
  - `year`: "FY24" (假设当前上下文或根据 2024 推断为 FY24，需在 Prompt 中明确映射规则，或测试脚本中显式指定)
  - `scenario`: "Scenario1"
  - `function`: "IT Allocation" (关键词匹配)

## 3. 执行逻辑 (Execution Logic)
Agent 应生成如下工具调用或对应的 Pandas 代码逻辑：

### 工具调用方式
```json
{
  "tool_call": "calculate_allocated_costs",
  "parameters": {
    "target_bl": "CB",
    "year": "FY24",
    "scenario": "Scenario1",
    "function": "IT Allocation"
  }
}
```

### 内部实现逻辑 (Pandas)
```python
# 1. 筛选 CostDataBase (CDB) 表
# 找到所有 IT Allocation 相关的成本池
df_cdb = CostDataBase[
    (CostDataBase['Year'] == 'FY24') & 
    (CostDataBase['Scenario'] == 'Scenario1') & 
    (CostDataBase['Function'] == 'IT Allocation')
]

# 2. 筛选 Table7 (Driver Rate) 表
# 找到目标业务线 (CB) 对应的分摊比例
df_t7 = Table7[
    (Table7['Year'] == 'FY24') & 
    (Table7['Scenario'] == 'Scenario1') & 
    (Table7['BL'] == 'CB') &
    (Table7['Key'].isin(df_cdb['Key'].unique())) # 仅匹配相关的 Key
]

# 3. 聚合费率 (防止多条记录导致膨胀)
# 按 Month, Key 汇总 RateNo
df_rate = df_t7.groupby(['Month', 'Key'])['RateNo'].sum().reset_index()

# 4. 关联计算
# 左连接 CDB 和 Rate 表
df_merged = pd.merge(df_cdb, df_rate, on=['Month', 'Key'], how='left')

# 5. 计算分摊金额
# Amount * Rate
df_merged['Allocated_Amount'] = df_merged['Amount'] * df_merged['RateNo'].fillna(0)

# 6. 最终汇总
result = df_merged.groupby('Month')['Allocated_Amount'].sum()
```

## 4. 预期回答 (Expected Answer)
“根据计算，2024年 Scenario1 下，Consumer Banking (CB) 分摊到的 IT Allocation 费用按月明细如下：
- Oct: ...
- Nov: ...
...
**全年总计**: [Total Amount]”

## 5. 验证点
1.  **参数提取准确性**：能否正确从自然语言中提取 `CB`, `FY24`, `Scenario1`, `IT Allocation`。
2.  **工具路由**：能否正确选择 `calculate_allocated_costs` 工具。
3.  **多表关联**：是否正确执行了 `CostDataBase` 和 `Table7` 的 Join 操作。
4.  **计算逻辑**：是否先聚合了 Rate 再 Join，避免数据发散。
