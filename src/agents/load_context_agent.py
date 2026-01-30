from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage

from excel_agent.logger import get_logger

from excel_agent.business_metadata import resolve_table_names


if TYPE_CHECKING:
    from graph.graph import AgentState


logger = get_logger("excel_agent.agents.load_context")


def load_context_node(state: "AgentState") -> "AgentState":
    """初始化上下文节点"""
    # 提取最新的用户问题
    messages = state["messages"]
    user_query = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_query = msg.content
            break

    # 如果是第一次进入，初始化 retry_count
    retry_count = state.get("retry_count", 0)
    if retry_count is None:
        retry_count = 0

    # 初始化 trace_id (如果不存在)
    if not state.get("trace_id"):
        state["trace_id"] = str(uuid.uuid4())

    # 初始化表名列表（由 agent 节点注入）
    if not state.get("table_names"):
        state["table_names"] = resolve_table_names(
            user_query, state.get("intent_analysis")
        )


    state["user_query"] = user_query
    state["retry_count"] = retry_count
    state["error_message"] = state.get("error_message", "")  # 继承之前的错误（如果有）
    return state
