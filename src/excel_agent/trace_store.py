from typing import Dict, Any, Optional
import datetime

class TraceStore:
    """
    内存中的 Trace 存储，用于缓存 Agent 的执行状态，
    以便在收到用户反馈时可以回溯并生成知识文档。
    """
    
    _store: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def save_trace(cls, trace_id: str, state: Dict[str, Any]):
        """保存 Trace 快照"""
        if not trace_id:
            return
            
        # 创建深拷贝或提取关键字段，避免后续引用修改
        # 这里提取关键信息以减少内存占用
        snapshot = {
            "trace_id": trace_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "user_query": state.get("user_query"),
            "intent_analysis": state.get("intent_analysis"),
            "sql_query": state.get("sql_query"),
            "execution_result": state.get("execution_result"),
            "final_messages": [m.content for m in state.get("messages", []) if not isinstance(m, list)], # 简化消息记录
            "error_message": state.get("error_message")
        }
        
        cls._store[trace_id] = snapshot
        
        # 简单的清理策略：如果超过 1000 条，删除最早的 200 条
        if len(cls._store) > 1000:
            keys_to_delete = list(cls._store.keys())[:200]
            for k in keys_to_delete:
                del cls._store[k]
    
    @classmethod
    def get_trace(cls, trace_id: str) -> Optional[Dict[str, Any]]:
        """获取 Trace 快照"""
        return cls._store.get(trace_id)

    @classmethod
    def clear(cls):
        """清空存储"""
        cls._store.clear()
