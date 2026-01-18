# ExcelMind Backend Documentation

## 1. 概述
ExcelMind 后端基于 **FastAPI** 构建，集成了 **Pandas** 进行数据处理，**LangGraph** 进行智能体编排，以及 **ChromaDB** 作为知识库检索。它提供了一套完整的 API 用于 Excel 数据的加载、管理、分析和自然语言交互。

## 2. 技术栈
- **Web 框架**: FastAPI
- **数据处理**: Pandas
- **AI/Agent**: LangChain, LangGraph, OpenAI SDK
- **向量数据库**: ChromaDB
- **配置管理**: YAML + Pydantic

## 3. API 接口详解

### 3.1 基础与状态
- **GET /**: 返回前端页面或 API 说明。
- **GET /status**: 获取当前系统状态。
  - 返回: `excel_loaded` (bool), `tables` (list), `active_table` (dict)。
- **POST /reset**: 重置 Agent 状态（清空所有表）。

### 3.2 表格管理 (Table Management)
支持多表加载和切换。
- **POST /upload**: 上传 Excel 文件。
  - 参数: `file` (File), `sheet_name` (Optional[str])
- **POST /load**: 通过本地路径加载 Excel。
  - 参数: `file_path` (str), `sheet_name` (Optional[str])
- **GET /tables**: 获取已加载的表列表。
- **PUT /tables/active**: 切换当前活跃表。
  - 参数: `table_id` (str)
- **DELETE /tables/{table_id}**: 删除指定表。
- **GET /tables/{table_id}/columns**: 获取指定表的列名。

### 3.3 表格连接 (Table Join)
- **POST /tables/join**: 执行表连接操作。
  - 参数: `table1_id`, `table2_id`, `keys1` (list), `keys2` (list), `join_type`, `new_name`
- **POST /tables/suggest-join**: AI 智能分析并建议连接配置。
  - 参数: `table1_id`, `table2_id`
  - 返回: 建议的连接键和类型。

### 3.4 对话与分析 (Chat & Analysis)
- **POST /chat**: 发送消息并获取响应（非流式）。
  - 参数: `message` (str), `history` (list)
- **POST /chat/stream**: 发送消息并获取流式响应（SSE）。
  - 返回: SSE 事件流，包含 `token` 或 `tool_calls`。

### 3.5 知识库 (Knowledge Base)
- **GET /knowledge**: 获取知识条目列表。
- **POST /knowledge**: 创建新知识条目。
- **GET /knowledge/{item_id}**: 获取详情。
- **PUT /knowledge/{item_id}**: 更新条目。
- **DELETE /knowledge/{item_id}**: 删除条目。
- **POST /knowledge/search**: 语义检索知识。
- **POST /knowledge/upload**: 上传知识文件 (.md/.txt)。
- **POST /knowledge/index**: 索引 knowledge 目录。

## 4. Agent 能力 (Tools)
Agent 内置了以下工具，可根据用户指令自动调用：
1.  **filter_data**: 数据筛选（支持多条件、逻辑运算）。
2.  **aggregate_data**: 单列聚合（sum, mean, count, max, min 等）。
3.  **group_and_aggregate**: 分组聚合统计。
4.  **search_data**: 全局或指定列关键词搜索。
5.  **get_column_stats**: 获取列的详细统计（分布、空值等）。
6.  **get_unique_values**: 获取列的唯一值分布。
7.  **generate_chart**: 生成 ECharts 图表配置（支持 bar, line, pie, scatter, radar, funnel）。
8.  **calculate**: 执行数学计算。
9.  **get_data_preview**: 查看数据前几行。

## 5. 数据结构
### TableInfo
```json
{
  "id": "uuid",
  "filename": "data.xlsx",
  "sheet_name": "Sheet1",
  "total_rows": 100,
  "total_columns": 10,
  "is_active": true,
  "is_joined": false
}
```

### KnowledgeItem
```json
{
  "id": "kb_xxx",
  "title": "知识标题",
  "content": "知识内容...",
  "category": "general",
  "tags": ["tag1", "tag2"]
}
```
