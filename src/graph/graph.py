"""LangGraph 工作流定义 - SQL 自修正闭环"""

from langchain_core.messages.base import BaseMessage
from typing import Annotated, Any, Dict, List, Literal, TypedDict, Optional

from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from excel_agent.logger import get_logger

from agents.load_context_agent import load_context_node
from agents.intent_analysis_agent import analyze_intent_node
from agents.sql_generation_agent import generate_sql_node
from agents.sql_validation_agent import validate_sql_node
from agents.execute_sql_agent import execute_sql_node
from agents.result_review_agent import review_result_node
from agents.refine_answer_agent import refine_answer_node

logger = get_logger("graph")


class AgentState(TypedDict):
    """Agent 状态"""

    trace_id: Annotated[Optional[str], lambda x, y: y]  # 会话追踪 ID
    messages: Annotated[List[BaseMessage], add_messages]

    # 意图分析
    intent_analysis: Annotated[Any, lambda x, y: y]  # Optional[IntentAnalysisResult]
    # SQL 流程状态
    user_query: Annotated[Optional[str], lambda x, y: y]
    sql_query: Annotated[Optional[str], lambda x, y: y]
    sql_valid: Annotated[bool, lambda x, y: y]
    execution_result: Annotated[
        Optional[str], lambda x, y: y
    ]  # 可能是 DataFrame string 或 error message
    review_passed: Annotated[Optional[bool], lambda x, y: y]
    review_message: Annotated[Optional[str], lambda x, y: y]

    # SQL Server 表名（由 agent 节点注入）
    table_names: Annotated[Optional[List[str]], lambda x, y: y]

    # 使用 operator.add 或者自定义 reducer 来处理并发更新，或者简单地覆盖
    # 这里我们希望后面的覆盖前面的，或者只接受一个。
    # 为了解决 InvalidUpdateError，我们显式声明它总是接受新值（覆盖）
    error_message: Annotated[Optional[str], lambda x, y: y]
    retry_count: Annotated[Optional[int], lambda x, y: y]


class AnalysisResult(TypedDict):
    """意图分析结果"""

    intent: Optional[str]
    params: Optional[Dict[str, Any]]
    error: Optional[str]


def reset_analysis(state: AgentState) -> AgentState:
    state["intent_analysis"] = None
    """重置意图分析状态"""
    return state


def route_after_validation(
    state: AgentState,
) -> Literal["execute_sql", "generate_sql", "refine_answer"]:
    """验证后的路由"""
    if state["sql_valid"]:
        return "execute_sql"

    if state["retry_count"] >= 5:
        # 重试次数过多，直接去生成回答（报告错误）
        logger.info(f'route_after_validation retry_count{state["retry_count"]}')
        return "refine_answer"

    return "generate_sql"


def route_after_execution(
    state: AgentState,
) -> Literal["review_result", "analyze_intent", "generate_sql"]:
    """执行后的路由"""
    error = state.get("error_message", "")
    if not error:
        logger.info(
            f' route_after_execution not error retry_count{state["retry_count"]}'
        )
        return "review_result"

    if state["retry_count"] >= 5:
        logger.info(f'route_after_execution retry_count{state["retry_count"]}')
        return "review_result"
    # 如果重试次数超过一定阈值（例如2次），且仍有错误，尝试重新分析意图
    # 这有助于处理因意图理解偏差导致的持续执行错误
    if state["retry_count"] > 2:
        state["intent_analysis"] = None
        return "analyze_intent"

    return "generate_sql"


def route_after_review(
    state: AgentState,
) -> Literal["refine_answer", "generate_sql", "analyze_intent"]:
    """结果审查后的路由"""
    if state.get("review_passed"):
        return "refine_answer"

    if state.get("retry_count", 0) >= 5:
        return "refine_answer"

    if state.get("retry_count", 0) > 2:
        state["intent_analysis"] = None
        return "analyze_intent"

    return "generate_sql"


def build_graph() -> StateGraph:
    """构建 SQL 自修正工作流"""

    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("load_context", load_context_node)
    workflow.add_node("analyze_intent", analyze_intent_node)
    workflow.add_node("generate_sql", generate_sql_node)
    workflow.add_node("validate_sql", validate_sql_node)
    workflow.add_node("execute_sql", execute_sql_node)
    workflow.add_node("review_result", review_result_node)
    workflow.add_node("refine_answer", refine_answer_node)

    # 设置入口
    workflow.set_entry_point("analyze_intent")

    # 边连接
    workflow.add_edge("analyze_intent", "load_context")
    workflow.add_edge("load_context", "generate_sql")
    workflow.add_edge("generate_sql", "validate_sql")
    workflow.add_conditional_edges(
        "validate_sql",
        route_after_validation,
        {
            "execute_sql": "execute_sql",
            "generate_sql": "generate_sql",
            "refine_answer": "refine_answer",
        },
    )
    workflow.add_conditional_edges(
        "execute_sql",
        route_after_execution,
        {
            "review_result": "review_result",
            "generate_sql": "generate_sql",
            "analyze_intent": "analyze_intent",
        },
    )

    workflow.add_conditional_edges(
        "review_result",
        route_after_review,
        {
            "refine_answer": "refine_answer",
            "generate_sql": "generate_sql",
            "analyze_intent": "analyze_intent",
        },
    )

    workflow.add_edge("refine_answer", END)

    return workflow.compile()


# 全局图实例
_graph = None


def get_graph():
    """获取图实例"""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def reset_graph():
    """重置图实例"""
    global _graph
    _graph = None
