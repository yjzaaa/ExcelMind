from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage

from excel_agent.logger import get_logger
from excel_agent.schemas import IntentAnalysisResult
from excel_agent.tools import ALL_TOOLS

from agents.llm import get_llm
from promts import SQL_GENERATION_PROMPT, render_prompt
from sqlserver import get_schema_context


if TYPE_CHECKING:
    from graph.graph import AgentState


logger = get_logger("excel_agent.agents.sql_generation")


def generate_sql_node(state: "AgentState") -> "AgentState":
    try:
        """SQL 生成节点 (实际生成 Pandas 代码)"""
        # logger.info("Starting SQL generation.")
        excel_summary = get_schema_context(state.get("table_names"))

        user_query = state["user_query"]
        intent_analysis = state.get("intent_analysis", "")

        # 如果是 Pydantic 对象，转换为 JSON 字符串以便在 prompt 中使用
        if isinstance(intent_analysis, IntentAnalysisResult):
            intent_analysis = intent_analysis.model_dump_json(indent=2)

        error_context = state.get("error_message", "")

        if error_context:
            # logger.info(
            #     f"Retrying SQL generation with error context: {error_context[:50]}..."
            # )
            error_context = (
                f"上一次尝试失败，错误信息：{error_context}。请根据错误修正代码。"
            )

        prompt = render_prompt(
            SQL_GENERATION_PROMPT,
            excel_summary=excel_summary,
            intent_analysis=intent_analysis,
            user_query=user_query,
            error_context=error_context,
        )

        llm = get_llm()

        # 获取所有可用的工具定义（为了让 LLM 知道有 get_service_details 等工具）
        tools = ALL_TOOLS

        # 使用 bind_tools 将工具信息传递给 LLM，允许它选择调用工具而不是生成代码
        llm_with_tools = llm.bind_tools(tools)

        # 使用 invoke 生成 SQL 或 工具调用
        response = llm_with_tools.invoke([HumanMessage(content=prompt)])

        # 检查是否有 tool_calls
        if response.tool_calls:
            tool_call = response.tool_calls[0]
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # logger.info(f"LLM generated tool call: {tool_name}")

            # 构造 JSON 指令字符串
            import json

            sql = json.dumps(
                {"tool_call": tool_name, "parameters": tool_args}, ensure_ascii=False
            )
        else:
            # 清理 markdown 标记
            sql = response.content.replace("```python", "").replace("```", "").strip()
            # logger.info("LLM generated Pandas code.")

        state["sql_query"] = sql
        state["retry_count"] = state["retry_count"] + 1
        return state
    except Exception as e:
        # logger.error(f"SQL generation failed: {str(e)}", exc_info=True)
        state["error_message"] = f"generate_sql节点执行错误。错误详情：{str(e)}"
        return state
