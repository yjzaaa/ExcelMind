# ExcelMind v1.1 技术蓝图

> 本文档记录 ExcelMind 下一版本（v1.1）的技术架构设计，聚焦于扩展 AI 操作 Excel 的能力边界和引入 Skills 架构。

---

## 一、当前架构分析

### 1.1 现有架构

```
Excel 文件 → pandas.read_excel() → DataFrame (内存) → LLM 工具调用
```

### 1.2 当前限制

| 限制 | 说明 |
|------|------|
| 只读不写 | 无法修改 Excel 内容 |
| 公式丢失 | pandas 只读取计算后的值 |
| 格式丢失 | 字体、颜色、边框等信息丢失 |
| 大文件风险 | 全量加载可能 OOM |
| 工具臃肿 | 工具数量增加会挤压上下文 |

---

## 二、目标架构

### 2.1 双引擎模式

```
┌─────────────────────────────────────────────────────────────────┐
│                     Excel 双引擎架构                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐         ┌──────────────┐                      │
│  │   pandas     │         │  openpyxl    │                      │
│  │  DataFrame   │  <───>  │  Workbook    │                      │
│  │  (分析引擎)   │   同步   │  (操作引擎)   │                      │
│  └──────────────┘         └──────────────┘                      │
│                                                                 │
│  分析引擎职责:                 操作引擎职责:                     │
│  • 快速查询筛选               • 读取/写入公式                   │
│  • 聚合统计                   • 修改单元格                      │
│  • 分组计算                   • 格式样式设置                    │
│  • 数据搜索                   • 工作表管理                      │
│                               • 文件保存                        │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 为什么需要双引擎？

| 引擎 | 优势 | 劣势 |
|------|------|------|
| **pandas** | 查询快（比 openpyxl 快 10-100 倍）、语法简洁 | 丢失公式/格式、只读 |
| **openpyxl** | 保留公式/格式、支持写入 | 查询慢、需手写循环 |

**结论: 各司其职，取长补短**

### 2.3 数据加载方式

```
只读一次文件，构建两个视图:

1. openpyxl 加载 → Workbook 对象 (保留结构)
2. 从 Workbook 提取数据 → pandas DataFrame (快速查询)

写入时:
- 直接操作 Workbook
- 按需同步到 DataFrame
```

---

## 三、能力边界定义

### 3.1 完全支持

| 能力 | 说明 |
|------|------|
| 数据读取 | 读取值、统计、搜索、筛选 |
| 数据写入 | 写入单元格、插入/删除行列 |
| 公式读取 | 获取单元格公式文本 |
| 公式写入 | 添加公式到单元格 |
| 格式样式 | 字体、颜色、边框、对齐 |
| 图表生成 | 在 Excel 内创建图表 |
| 工作表管理 | 创建、删除、重命名 sheet |

### 3.2 有限支持

| 能力 | 限制说明 |
|------|---------|
| 公式计算 | openpyxl 不执行计算，需保存后用 Excel 打开 |
| 透视表 | 可读取，创建功能有限 |
| 复杂图表 | 基础图表支持好，高级图表有限 |

### 3.3 不支持

| 能力 | 原因 |
|------|------|
| VBA 宏 | openpyxl 不执行代码 |
| 实时公式计算 | 需要 Excel 引擎 |
| .xls 格式 | openpyxl 仅支持 .xlsx |

---

## 四、工具架构设计：Skills 模式 (基于 MCP 标准)

### 4.1 架构演进：从 Tools 到 Skills

传统的 Function Calling 模式存在上下文窗口挤压和工具选择准确性问题。v1.1 将引入符合现代 Agent 设计模式的 **Skills (技能)** 架构。

**核心理念：**
- **原子性 (Atomicity)**: 每个 Tool 保持功能单一。
- **组合性 (Composability)**: Skill 是 Tools 的逻辑集合，面向特定任务领域。
- **上下文感知 (Context-Awareness)**: 根据用户意图动态加载/卸载 Skills。

### 4.2 动态 Skills 加载机制

```
┌─────────────────────────────────────────────────────────────┐
│                   动态 Skills 路由引擎                       │
│                                                             │
│  用户消息                                                   │
│     ↓                                                       │
│  意图识别 (Intent Recognition)                              │
│     │                                                       │
│     ├──> 关键词匹配 (Deterministic) -> 快速路径             │
│     └──> 向量语义检索 (Probabilistic) -> 泛化路径           │
│             ↓                                               │
│  Skill Registry (技能注册表)                                │
│     ├── Skill A: 数据清洗 (Tools: filter, clean, dedup)     │
│     ├── Skill B: 可视化 (Tools: chart, style)               │
│     └── Skill C: 公式计算 (Tools: formula, calc)            │
│             ↓                                               │
│  Active Context (当前上下文)                                │
│     └── 仅注入相关 Skills 的 Tools 定义 -> LLM              │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Skill 定义规范

每个 Skill 是一个包含以下元数据的配置对象：

```python
class SkillDefinition:
    name: str          # 技能唯一标识, e.g., "data_visualization"
    description: str   # 用于语义检索的自然语言描述
    tools: List[Tool]  # 包含的具体工具列表
    examples: List[str]# 用户指令示例 (Few-shot)
    activation: dict   # 激活条件配置
        keywords: List[str] # 强触发词
        threshold: float    # 语义相似度阈值
```

### 4.4 技能分类

```
1. Core Skills (核心技能 - 始终激活)
   ├── query_data       - 通用数据查询与探索
   └── project_info     - 获取表格元数据和上下文

2. On-Demand Skills (按需加载 - 意图触发)
   ├── Data Modification - 数据修改 (write, update, delete)
   ├── Formatting        - 格式美化 (style, color, font)
   ├── Analytics         - 高级分析 (formula, pivot)
   └── Visualization     - 图表生成 (charts)

3. System Skills (系统技能 - 流程控制)
   ├── File IO           - 保存、另存为、导出
   └── Batch Process     - 批处理任务
```

### 4.5 工具合并策略 (Tool Coalescing)

为了进一步减少 Token 消耗，我们将采用 **操作参数化 (Operation Parameterization)** 策略，将多个细粒度工具合并为通用工具。

**示例：数据查询 Skill**

```python
# 合并前 (多个独立工具)
filter_data(), aggregate_data(), group_data(), search_data()

# 合并后 (单个多态工具)
query_data(
    operation: str, # "filter" | "aggregate" | "group" | "search"
    params: dict    # 根据 operation 变化的参数对象
)
```

优点：
- 减少函数头定义 (Function Header Overhead)
- 让模型更专注于"我要查询"这一高层意图，而非纠结具体的函数名

---

## 五、核心模块设计

### 5.1 ExcelDocument 类

```
职责:
- 管理双引擎 (DataFrame + Workbook)
- 数据同步 (Lazy Syncing 策略)
- 变更追踪 (Change Tracking)
- 事务管理 (Transaction Management for Writes)

属性:
- dataframe: pandas.DataFrame
- workbook: openpyxl.Workbook
- file_path: str
- is_dirty: bool
- active_sheet: str

方法:
- load(path)
- save(path)
- sync_workbook_to_df()
- sync_df_to_workbook() # 仅在需要全量写回时使用
- get_write_engine() -> Workbook
- get_read_engine() -> DataFrame
```

### 5.2 SkillManager 类

```
职责:
- 维护 Skill Registry
- 实时意图分析
- Tool 上下文注入

方法:
- register_skill(skill_def)
- resolve_skills(user_query) -> List[Tool]
- get_system_prompt_additions() # 获取激活技能的额外指令
```

---

## 六、待探索方向

### 6.1 本地代码解释器 (Code Interpreter)

- 这是一个特殊的 High-Level Skill。
- 允许模型直接编写并执行 Python 代码操作 DataFrame/Workbook。
- 优势：灵活性无限，解决复杂逻辑。
- 挑战：沙箱安全，环境依赖。
- 在 v1.1 中作为 **实验性特性** 考虑。

### 6.2 混合运行时 (Hybrid Runtime)

- 探索 `xlwings` 或 `win32com` (Windows Only) 作为可选的 backend。
- 当检测到本地环境支持 Excel COM 时，自动切换以支持真实公式计算。

---

## 七、版本规划

### v1.1 核心目标 (Foundation)

1. ✅ **双引擎架构**: 引入 openpyxl 与 pandas 并行。
2. ✅ **Skills 架构**: 实现基于意图的动态工具加载。
3. ✅ **操作能力**: 实现基础的写入 (Write) 和公式读取 (Read Formula)。
4. ✅ **工具重构**: 将查询类工具合并为 `query_data`。

### v1.2 扩展目标 (Enhancement)

1. 样式与格式化 Skill (完整支持)。
2. 原生图表写入 Skill。
3. 实验性代码解释器 Skill。

---

*文档创建时间: 2025-12-31*
*版本: Draft v1.1*
