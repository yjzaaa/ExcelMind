# 业务逻辑与规则定义

本文档由 Excel 数据源自动生成，旨在为 AI 模型提供核心业务逻辑、字段映射及典型问题的处理范式。

## 1. 字段映射与术语解释

下表定义了核心数据表（CostDataBase 和 Table7）中关键字段的业务含义。

### CostDataBase (主数据表)

| 字段名 | 业务含义 | 备注 |
|:---|:---|:---|
| **Year** | 年份 / 年度 / 财年 | 核心时间维度 |
| **Scenario** | 版本 | 如 Budget1 (预算), Actual (实际数) |
| **Budget1** | 预算 | 别名: BGT, Budget, BGT1 |
| **Actual** | 实际数 | 别名: Act |
| **Function** | 费用类型 / 职能部门 | 费用产生自哪个职能部门 (如 HR, IT, Procurement) |
| **Cost text** | 服务项 / 服务内容 | 合同内容，服务名称 |
| **Account** | 总账科目 | |
| **Category** | 成本类型 / 分类 | |
| **Functional Cost** | Global Function Cost | 直接入 Global function cost center 的费用 |
| **Cost Center Cost** | BL Cost | 直接入 BL cost center 的费用 |
| **Key** | 分摊依据 / 分摊标准 | **核心字段**：用于关联 Table7 的分摊逻辑名称 |
| **Month** | 月份数据 | Oct, Nov, Dec ... Sep (财年从 Oct 开始) |
| **Year Total** | 全年总计 | 12个月份的汇总 |

### Table7 (分摊规则表)

| 字段名 | 业务含义 | 备注 |
|:---|:---|:---|
| **Fiscal Year** | 财年 | 对应 CostDataBase 的 Year |
| **Scenario** | 版本 | 对应 CostDataBase 的 Scenario |
| **Period** | 所属期 | 具体月份或全年 |
| **Key** | 分摊逻辑名称 | 与 CostDataBase 的 Key 字段关联 |
| **CC** | Cost Center | 成本中心 |
| **BL** | 业务线 / 部门 | 被分摊的对象 (如 CT, DT) |
| **RateNo** | 分摊比例 | 矩阵中的百分比 (某月、某CC、某Key的分摊比例) |

---

## 2. 典型业务问题与解决逻辑 (Q&A Examples)

以下案例展示了如何将自然语言问题转化为具体的数据查询和计算步骤。

### Q1: IT费用包括哪些服务？分摊依据是什么？
> **User Question**: What services do IT cost include? And what is the allocation key?

*   **逻辑步骤**:
    1.  **筛选**: 在 `CostDataBase` 中筛选 `Function == 'IT'`。
    2.  **提取**: 列出不重复的 `Cost text` (服务) 和对应的 `Key` (分摊依据)。
    3.  **细化**: 如果未指定年份/场景，应分别列出所有年度或追问用户。

### Q2: FY26 计划了多少 HR 费用预算？
> **User Question**: What was the HR Cost in FY26 BGT?

*   **逻辑步骤**:
    1.  **筛选**:
        *   Table: `CostDataBase`
        *   Year: `FY26`
        *   Scenario: `Budget1`
        *   Function: `HR`
    2.  **计算**:
        *   若问全年：SUM(`Mouth`) 或取 `Year Total`。
        *   若问具体月份：汇总对应月份的费用。

### Q3: FY25 实际分摊给 CT 的 IT 费用是多少？(核心分摊逻辑)
> **User Question**: What was the actual IT cost allocated to CT in FY25?

*   **逻辑步骤**:
    1.  **Step 1 (主表筛选)**: 在 `CostDataBase` 中筛选：
        *   Year: `FY25`
        *   Scenario: `Actual`
        *   Function: `IT Allocation`
        *   *获取*: 每月发生的金额 (Amount) 和 分摊 Key。
    2.  **Step 2 (费率获取)**: 在 `Table7` 中筛选：
        *   Year: `FY25`
        *   Scenario: `Actual`
        *   Key: (来自 Step 1 的 Key)
        *   BL: `CT` (目标业务线)
        *   *获取*: 每月的分摊比例 (Rate)。
    3.  **Step 3 (计算)**:
        *   计算公式: `Allocated Amount = Amount (from CostDataBase) * Rate (from Table7)`
        *   按月计算后汇总全年。

### Q4: 采购费用从 FY25 Actual 到 FY26 BGT 的变化？
> **User Question**: How does Procurement Cost change from FY25 Actual to FY26 BGT?

*   **逻辑步骤**:
    1.  **Step 1 (基准值)**: 计算 FY25 Actual 采购费用 (Function='Procurement')。
    2.  **Step 2 (目标值)**: 计算 FY26 Budget1 采购费用。
    3.  **Step 3 (对比)**:
        *   变化金额 = 目标值 - 基准值
        *   变化比例 = (目标值 - 基准值) / 基准值

### Q5: 分摊给 4130011 的 HR 费用变化 (FY26 BGT vs FY25 Actual)
> **User Question**: How is the change of HR allocation to 4130011 between FY26 BGT and FY25 Actual?

*   **逻辑步骤**:
    1.  **Step 1**: 计算 FY25 Actual 分摊给 `CC=4130011` 的 HR 费用。
        *   需关联 `CostDataBase` (Function='HR Allocation') 和 `Table7` (CC='4130011')。
    2.  **Step 2**: 计算 FY26 Budget1 分摊给 `CC=4130011` 的 HR 费用。
    3.  **Step 3**: 计算两者差异 (金额和比例)。
