from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage

from excel_agent.logger import get_logger
from excel_agent.schemas import IntentAnalysisResult
from sqlserver import get_schema_context
from excel_agent.business_metadata import resolve_table_names

from promts import INTENT_ANALYSIS_PROMPT, render_prompt
from agents.llm import get_llm


if TYPE_CHECKING:
    from graph.graph import AgentState


logger = get_logger("excel_agent.agents.intent_analysis")


def analyze_intent_node(state: "AgentState") -> "AgentState":
    """意图分析节点"""
    try:
        # logger.info(
        #     f"Starting intent analysis. Retry count: {state.get('retry_count', 0)}"
        # )
        user_query = state.get("user_query", "")
        if not user_query:
            for msg in reversed(state.get("messages", [])):
                if isinstance(msg, HumanMessage):
                    user_query = msg.content
                    break
        table_names = state.get("table_names") or resolve_table_names(
            user_query, state.get("intent_analysis")
        )
        state["table_names"] = table_names
        excel_summary = get_schema_context(table_names)
        error_context = state.get("error_message", "")

        additional_instruction = ""
        if error_context:
            # logger.info(
            #     "Detected missing parameter error, adding instruction to prompt."
            # )
            additional_instruction = (
                f"\n\n⚠️ 上一次尝试失败，错误信息：{error_context}。"
                "\n请务必仔细检查用户问题，重新提取缺失的参数。"
            )

        prompt = (
            render_prompt(
                INTENT_ANALYSIS_PROMPT,
                excel_summary=excel_summary,
                user_query=user_query,
            )
            + additional_instruction
        )

        llm = get_llm()
        response = llm.invoke([HumanMessage(content=prompt)])
        state["intent_analysis"] = response

        # logger.debug(f"Intent analysis result: {response.content[:100]}...")
        return state
    except Exception as e:
        # logger.error(f"Intent analysis failed: {str(e)}", exc_info=True)
        state["error_message"] = f"意图分析节点执行错误。错误详情：{str(e)}"
        return state
