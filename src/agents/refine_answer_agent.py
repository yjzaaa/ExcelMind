from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage

from excel_agent.logger import get_logger

from agents.llm import get_llm
from promts import ANSWER_REFINEMENT_PROMPT, render_prompt


if TYPE_CHECKING:
    from graph.graph import AgentState


logger = get_logger("excel_agent.agents.refine_answer")


def refine_answer_node(state: "AgentState") -> "AgentState":
    """生成最终回答节点"""
    # logger.info("Refining final answer.")
    user_query = state["user_query"]
    sql = state.get("sql_query", "未生成 SQL")
    execution_result = state.get("execution_result", "无结果")

    prompt = render_prompt(
        ANSWER_REFINEMENT_PROMPT,
        user_query=user_query,
        sql_query=sql,
        execution_result=execution_result,
    )

    # 强化安全检查：如果执行结果包含错误，强制追加系统警告
    if (
        "error" in str(execution_result).lower()
        or "exception" in str(execution_result).lower()
    ):
        # logger.warning("Execution result contains errors, adding warning to prompt.")
        prompt += (
            "\n\n⚠️ SYSTEM WARNING: 检测到执行结果包含错误信息。"
            "你必须停止尝试回答用户的问题数据。**绝对禁止**输出任何数据表格或数值。请仅解释错误原因。"
        )

    llm = get_llm()
    response = llm.invoke([HumanMessage(content=prompt)])
    state["messages"] = [response]

    # logger.info("Final answer generated.")
    return state
