from __future__ import annotations

from typing import TYPE_CHECKING

from excel_agent.logger import get_logger
from excel_agent.tools import ALL_TOOLS
from sqlserver import execute_sql_query


if TYPE_CHECKING:
    from graph.graph import AgentState


logger = get_logger("excel_agent.agents.execute_sql")


def execute_sql_node(state: "AgentState") -> "AgentState":
    """SQL 执行节点 (实际执行 Pandas 或直接调用工具)"""
    # logger.info("Starting execution.")
    sql = state["sql_query"]

    # 检查是否为工具调用指令 (JSON 格式)
    if sql.strip().startswith("{") and "tool_call" in sql:
        import json

        try:
            tool_data = json.loads(sql)
            tool_name = tool_data.get("tool_call")
            params = tool_data.get("parameters", {})

            # logger.info(f"Executing tool: {tool_name}")

            # 查找对应工具
            target_tool = None
            for tool in ALL_TOOLS:
                if tool.name == tool_name:
                    target_tool = tool
                    break

            if target_tool:
                result = target_tool.invoke(params)

                # 处理工具返回结果
                if isinstance(result, dict) and "error" in result and result["error"]:
                    # logger.error(f"Tool execution failed: {result['error']}")
                    state["error_message"] = f"工具执行错误: {result['error']}"
                    return state

                state["execution_result"] = str(result)
                state["error_message"] = ""
                # logger.info("Tool execution successful.")
                return state
            else:
                # logger.error(f"Tool not found: {tool_name}")
                state["error_message"] = f"未找到工具: {tool_name}"
                return state

        except json.JSONDecodeError:
            # logger.warning("JSON decode failed, falling back to Pandas execution.")
            pass  # 如果解析失败，尝试作为普通 SQL 执行
        except Exception as e:
            # logger.error(f"Tool parsing failed: {str(e)}", exc_info=True)
            state["error_message"] = f"工具调用解析失败: {str(e)}"
            return state

    # 直接执行 SQL Server 查询
    # logger.info("Executing SQL Server query.")
    try:
        cleaned_sql = sql.strip()
        if cleaned_sql.lower().startswith("sql"):
            cleaned_sql = cleaned_sql[3:].lstrip()
        if cleaned_sql.startswith("```"):
            cleaned_sql = cleaned_sql.strip("`").lstrip()
        df = execute_sql_query(cleaned_sql)
        result_str = df.to_string(index=False)
        # logger.info("SQL Server execution successful.")
        state["execution_result"] = result_str
        state["error_message"] = ""
        return state
    except Exception as e:
        # logger.warning(f"SQL Server execution failed: {e}")
        state["error_message"] = f"执行出错: {str(e)}"
        return state
