# 分摊计算类（跨表关联）

> 适用：分摊金额 = 基础金额 × 分摊比例，跨表四重匹配。

## Q3：FY25 实际分摊给 CT 的 IT 费用是多少？

**需求特征**：双表联查 + BL 维度分摊 + 聚合。

**执行建议**：调用 `generate_alloc_sql()` 生成 SQL，再执行。

**伪代码**

```python
sql = generate_alloc_sql(['FY25'], ['Actual'], 'IT Allocation', 't7.[BL]', "'CT'")
```

## Q4：分摊给 413001 的 HR 费用变化（FY26 BGT vs FY25 Actual）

**需求特征**：双表联查 + CC 维度 + 跨周期对比。

**伪代码**

```python
sql = generate_alloc_sql(['FY26','FY25'], ['Budget1','Actual'], 'HR Allocation', 't7.[CC]', "'413001'")
```

## Q7：FY26 Budget1 分摊给 413001 vs FY25 Actual 分摊给 XP（跨维度跨周期）

**需求特征**：不同周期与维度，按规则优先使用 CC；如 CC 在 BL 范围内优先 CC。

**伪代码**

```python
sql_a = generate_alloc_sql(['FY26'], ['Budget1'], 'HR Allocation', 't7.[CC]', "'413001'")
sql_b = generate_alloc_sql(['FY25'], ['Actual'], 'HR Allocation', 't7.[CC]', "'413001'")
```
