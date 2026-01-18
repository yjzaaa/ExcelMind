import os
import json
from datetime import datetime
from pathlib import Path
from .trace_store import TraceStore
from .knowledge_base import get_knowledge_base, KnowledgeItem
from .schemas import IntentAnalysisResult

class FeedbackManager:
    """
    反馈管理器
    负责处理用户反馈，并将正确的高质量问答转化为知识文档
    """
    
    def __init__(self, knowledge_dir: str = "knowledge/confirmed_qa"):
        self.knowledge_dir = Path(knowledge_dir)
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        
    def handle_feedback(self, trace_id: str, is_correct: bool, user_comment: str = None) -> str:
        """
        处理用户反馈
        
        Args:
            trace_id: 会话 Trace ID
            is_correct: 用户是否认为回答正确
            user_comment: 用户备注（可选）
            
        Returns:
            处理结果消息
        """
        if not is_correct:
            # TODO: 处理负反馈（例如记录到错误日志供离线分析）
            return "Negative feedback recorded"
            
        # 1. 获取 Trace 快照
        trace = TraceStore.get_trace(trace_id)
        if not trace:
            return "Trace not found"
            
        # 2. 检查必要字段是否存在
        if not trace.get("intent_analysis") or not trace.get("sql_query"):
            return "Incomplete trace data, cannot generate knowledge"
            
        # 3. 生成 Markdown 知识文档
        try:
            doc_content = self._generate_markdown(trace, user_comment)
            
            # 4. 写入文件
            file_name = f"{trace_id}.md"
            file_path = self.knowledge_dir / file_name
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(doc_content)
                
            # 5. 触发知识库索引
            kb = get_knowledge_base()
            if kb:
                # 构造 KnowledgeItem
                item = KnowledgeItem(
                    id=f"qa_confirmed_{trace_id}",
                    content=doc_content,
                    title=f"QA: {trace.get('user_query', 'Unknown Query')}",
                    category="confirmed_qa",
                    tags=["auto-generated", "human-verified"],
                    priority="high",
                    source_file=str(file_path)
                )
                kb.add_entry(item)
                
            return f"Knowledge generated successfully: {file_name}"
            
        except Exception as e:
            return f"Error generating knowledge: {str(e)}"

    def _generate_markdown(self, trace: dict, user_comment: str = None) -> str:
        """根据 Trace 生成标准化的 Markdown 文档"""
        
        user_query = trace.get("user_query", "")
        intent_analysis = trace.get("intent_analysis", {})
        sql_query = trace.get("sql_query", "")
        final_answer = ""
        
        # 尝试从 final_messages 中提取最后一条 AI 回复
        msgs = trace.get("final_messages", [])
        if msgs:
            final_answer = msgs[-1]
            
        # 格式化 Intent Analysis
        intent_type = "unknown"
        parameters = {}
        reasoning = ""
        
        if isinstance(intent_analysis, dict):
            intent_type = intent_analysis.get("intent_type", "unknown")
            parameters = intent_analysis.get("parameters", {})
            reasoning = intent_analysis.get("reasoning", "")
        elif hasattr(intent_analysis, "model_dump"): # Pydantic model
            data = intent_analysis.model_dump()
            intent_type = data.get("intent_type", "unknown")
            parameters = data.get("parameters", {})
            reasoning = data.get("reasoning", "")
        
        # 格式化 JSON 参数
        params_json = json.dumps(parameters, ensure_ascii=False, indent=2)
        
        # 构建 Markdown 内容
        content = f"""---
id: qa_confirmed_{trace['trace_id']}
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
{params_json}
```
- **分析思路**: {reasoning}

## 执行逻辑 (标准答案)
```python
{sql_query}
```

## 最终回答
{final_answer}

## 验证信息
- **验证时间**: {datetime.now().isoformat()}
- **验证人**: User (Via Feedback API)
"""
        if user_comment:
            content += f"- **用户备注**: {user_comment}\n"
            
        return content

# 全局单例
_feedback_manager = None

def get_feedback_manager() -> FeedbackManager:
    global _feedback_manager
    if _feedback_manager is None:
        _feedback_manager = FeedbackManager()
    return _feedback_manager
