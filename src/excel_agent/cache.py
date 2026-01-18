import hashlib
import json
import time
from typing import Any, Dict, Optional, Tuple
from functools import lru_cache

class AgentCache:
    """Agent 缓存层，用于缓存意图分析、SQL 生成和 RAG 检索结果"""
    
    _intent_cache: Dict[str, Dict[str, Any]] = {}
    _rag_cache: Dict[str, str] = {}
    
    @staticmethod
    def _generate_key(query: str, context_hash: str = "") -> str:
        """生成缓存 Key"""
        content = f"{query.strip()}|{context_hash}"
        return hashlib.md5(content.encode()).hexdigest()
        
    @classmethod
    def get_intent(cls, query: str, context_hash: str = "") -> Optional[Dict[str, Any]]:
        """获取缓存的意图分析结果"""
        key = cls._generate_key(query, context_hash)
        entry = cls._intent_cache.get(key)
        
        if not entry:
            return None
            
        # 简单的过期策略 (例如 24 小时，这里暂不实现自动过期，依赖内存生命周期)
        return entry.get("data")
        
    @classmethod
    def set_intent(cls, query: str, data: Dict[str, Any], context_hash: str = ""):
        """设置意图分析缓存"""
        key = cls._generate_key(query, context_hash)
        cls._intent_cache[key] = {
            "data": data,
            "timestamp": time.time()
        }
        
    @classmethod
    def get_rag_context(cls, query: str) -> Optional[str]:
        """获取 RAG 检索结果缓存"""
        # RAG 结果只与 Query 有关 (假设知识库相对静态)
        key = hashlib.md5(query.strip().encode()).hexdigest()
        return cls._rag_cache.get(key)
        
    @classmethod
    def set_rag_context(cls, query: str, context: str):
        """设置 RAG 检索结果缓存"""
        key = hashlib.md5(query.strip().encode()).hexdigest()
        cls._rag_cache[key] = context

    @classmethod
    def clear(cls):
        """清空缓存"""
        cls._intent_cache.clear()
        cls._rag_cache.clear()

# 导出全局单例方法
get_intent_cache = AgentCache.get_intent
set_intent_cache = AgentCache.set_intent
get_rag_cache = AgentCache.get_rag_context
set_rag_cache = AgentCache.set_rag_context
