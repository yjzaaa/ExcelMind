# 将 SQL 查询示例嵌入知识库 (RAG) 计划

为了让 Agent 在运行时能够参考 `knowledge/sql_query_examples.md` 中的示例，我们需要将其索引到向量数据库中。

## 1. 创建索引脚本
我们将创建一个专用的 Python 脚本 `src/index_kb.py`，用于：
- 初始化 `KnowledgeBase` 实例。
- 扫描 `knowledge/` 目录下的所有 `.md` 文件。
- 将文件内容加载并转换为向量索引（Embedding）。
- 存入 ChromaDB 向量数据库。

## 2. 执行索引
运行上述脚本，完成知识库的构建。这将使 `sql_query_examples.md` 中的 `CostDataBase` 和 `Table7` 查询范式被系统“记住”。

## 3. 验证检索
编写一个简单的验证步骤（集成在索引脚本中或单独运行），模拟一个相关问题（例如：“如何查询 IT 费用？”），检查系统是否能正确检索到 `sql_query_examples.md` 中的内容。
