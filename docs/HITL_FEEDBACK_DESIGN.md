# Human-in-the-Loop (HITL) 结果确认与知识库自进化机制设计文档

## 1. 概述
在当前的前后端单体架构中，为了提升 Agent 对复杂业务逻辑处理的准确性，我们需要引入“人工确认”环节。通过捕捉用户对 Agent 回答的满意度反馈（特别是“确认正确”的场景），将高质量的问答链路（Query -> Intent -> Logic -> Result）固化为标准知识文档，存入 RAG 知识库。这将形成一个数据飞轮，使 Agent 能够从过往的正确案例中持续学习。

## 2. 核心目标
1.  **闭环反馈**：建立“问答-反馈-记录”的完整闭环。
2.  **思维链路固化**：不仅仅记录“问题-答案”，更重要的是记录“意图分析结果”和“执行逻辑（SQL/代码）”，即 Agent 的“思维链路”。
3.  **知识库自进化**：自动将确认正确的链路转换为 RAG 可检索的 Markdown 文档，供后续类似问题参考。

## 3. 架构设计

### 3.1 现有架构 (LangGraph)
当前流程：`Load Context` -> `Analyze Intent` -> `Generate SQL` -> `Execute` -> `Refine Answer` -> `End`

### 3.2 引入反馈机制后的流程
我们不需要打断当前的同步链条（避免阻塞用户），而是采用 **“事后异步反馈”** 模式。

1.  **会话 ID (Session ID)**: 为每一次问答生成唯一的 `trace_id`，并在 AgentState 中流转。
2.  **状态缓存**: 将 Agent 的中间执行状态（Intent, SQL, Result）临时缓存（如内存或 Redis）。
3.  **反馈接口**: 提供一个 API 接口 `/api/feedback`，接收用户对特定 `trace_id` 的评价。
4.  **知识生成**: 当收到 `positive` (正确) 反馈时，触发后台任务，将缓存的思维链路转换为 Markdown 文档并写入 `knowledge/confirmed_qa/` 目录。

## 4. 数据结构设计

### 4.1 思维链路快照 (Trace Snapshot)
当 Agent 完成回答时，应记录以下关键信息：

```json
{
  "trace_id": "uuid-v4",
  "timestamp": "2024-01-18T10:00:00Z",
  "user_query": "IT cost 有哪些服务",
  "intent_analysis": {
    "intent_type": "general_query",
    "parameters": {...},
    "reasoning": "用户询问..."
  },
  "generated_logic": "CostDataBase.query(\"Function == 'IT'\")",
  "final_answer": "IT 费用包含...",
  "execution_status": "success"
}
```

### 4.2 知识库文档模版 (Markdown)
当用户确认正确后，生成如下格式的文档（存放在 `knowledge/confirmed_qa/`）：

```markdown
---
id: qa_confirmed_{trace_id}
title: {user_query}
category: confirmed_qa
tags: [auto-generated, human-verified, {intent_type}]
priority: high
---

# 人工确认的问答链路

## 用户问题
{user_query}

## 意图分析 (正确范式)
- **意图类型**: {intent_type}
- **参数提取**:
```json
{parameters_json}
```
- **分析思路**: {reasoning}

## 执行逻辑 (标准答案)
```python
{generated_logic}
```

## 最终回答
{final_answer}

## 验证信息
- **验证时间**: {feedback_timestamp}
- **验证人**: User
```

## 5. 详细实现方案

### 步骤 1: 增加 Trace ID 支持
修改 `AgentState`，增加 `trace_id` 字段。在 `load_context_node` 初始化时生成。

### 步骤 2: 状态记录
在 `refine_answer_node` 结束前，将当前完整状态保存到全局字典 `TRACE_STORE` (模拟数据库) 中。
`TRACE_STORE[state["trace_id"]] = state`

### 步骤 3: 实现反馈处理逻辑
新增 `FeedbackManager` 类：

```python
class FeedbackManager:
    def handle_feedback(self, trace_id: str, is_correct: bool, user_correction: str = None):
        if is_correct:
            # 1. 获取缓存状态
            state = TRACE_STORE.get(trace_id)
            if not state:
                return "Trace not found"
            
            # 2. 生成知识文档
            doc_content = self._generate_markdown(state)
            
            # 3. 写入文件系统
            filename = f"knowledge/confirmed_qa/{trace_id}.md"
            with open(filename, "w") as f:
                f.write(doc_content)
                
            # 4. 触发知识库实时索引
            get_knowledge_base().add_entry(
                KnowledgeItem(id=f"qa_{trace_id}", content=doc_content, ...)
            )
            return "Knowledge captured"
        else:
            # (可选) 记录错误案例用于离线分析
            pass
```

### 步骤 4: RAG 检索增强
当前的 `analyze_intent_node` 和 `generate_sql_node` 已经集成了 RAG。
一旦新的 QA 文档被加入索引，下一次用户提问类似问题时：
1.  RAG 会检索到这个“人工确认的问答链路”。
2.  Prompt 会包含：“参考知识: 人工确认的问答链路...”。
3.  LLM 会倾向于模仿文档中的 `Intent Analysis` 和 `Execution Logic`，从而复现正确的行为。

## 6. 后续规划
1.  **负反馈闭环**: 对于用户标记为“错误”的 Case，提供界面让用户输入“正确做法”，系统将其转化为“修正规则”文档。
2.  **权重管理**: 给“人工确认”的知识条目更高的检索权重（Priority=high）。
3.  **自动清理**: 定期清理低价值或过时的 QA 快照。
