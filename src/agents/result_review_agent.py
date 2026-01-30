from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage

from excel_agent.logger import get_logger

from agents.llm import get_llm
from promts import RESULT_REVIEW_PROMPT, render_prompt


if TYPE_CHECKING:
    from graph.graph import AgentState


logger = get_logger("excel_agent.agents.result_review")


def review_result_node(state: "AgentState") -> "AgentState":
    """结果审查节点：判断结果是否足以回答问题"""
    try:
        user_query = state.get("user_query", "")
        sql = state.get("sql_query", "")
        execution_result = state.get("execution_result", "")

        prompt = render_prompt(
            RESULT_REVIEW_PROMPT,
            user_query=user_query,
            sql_query=sql,
            execution_result=execution_result,
        )

        llm = get_llm()
        response = llm.invoke([HumanMessage(content=prompt)])
        decision = response.content.strip()

        if decision.upper().startswith("PASS"):
            state["review_passed"] = True
            state["review_message"] = ""
            return state

        if decision.upper().startswith("RETRY"):
            state["review_passed"] = False
            state["review_message"] = decision
            state["error_message"] = decision
            return state

        # 兜底：无法解析则当作失败
        state["review_passed"] = False
        state["review_message"] = f"RETRY: 无法解析审查结果: {decision}"
        state["error_message"] = state["review_message"]
        return state
    except Exception as e:
        # logger.error(f"Result review failed: {str(e)}", exc_info=True)
        state["review_passed"] = False
        state["review_message"] = f"RETRY: 审查节点异常: {str(e)}"
        state["error_message"] = state["review_message"]
        return state
