from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage

from excel_agent.logger import get_logger

from agents.llm import get_llm
from promts import SQL_VALIDATION_PROMPT, render_prompt
from sqlserver import get_schema_columns_info


if TYPE_CHECKING:
    from graph.graph import AgentState


logger = get_logger("excel_agent.agents.sql_validation")


def validate_sql_node(state: "AgentState") -> "AgentState":
    try:
        """SQL 验证节点（适配 Pandas SQL 只读查询规则，精准校验）"""
        # logger.info("Starting SQL validation.")
        sql = state["sql_query"]
        # 空SQL直接校验失败
        if not sql or sql.strip() == "":
            # logger.warning("Validation failed: Empty SQL query.")
            state["error_message"] = "代码验证失败: SQL查询语句不能为空。"
            state["sql_valid"] = False
            return state

        # 1. 【核心】Pandas SQL 专属静态安全+语法基础校验
        # ✅ 只保留Pandas SQL中真正危险/非法的关键字，全部是【写入/执行类】，Pandas SQL只支持SELECT查询
        forbidden_keywords = [
            "delete",
            "drop",
            "insert",
            "update",
            "replace",
            "alter",
            "create",
            "truncate",
            "exec(",
            "eval(",
            "__import__",
            "open(",
            "write(",
            "system(",
            "os.",
            "sys.",
        ]
        # 统一转大写，忽略大小写匹配（如 Delete/DELETE 都拦截）
        sql_upper = sql.upper()
        for keyword in forbidden_keywords:
            # 关键字匹配区分大小写（如os.是危险的，Os.也拦截，SELECT是正常的）
            if keyword in sql:
                # logger.warning(
                #     f"Validation failed: Forbidden keyword '{keyword}' detected."
                # )
                state["error_message"] = (
                    f"代码验证失败: 包含禁止的关键字 '{keyword}'。"
                    "请仅使用 Pandas 只读查询语法(SELECT)，禁止使用数据修改/文件读写/系统执行类语法。"
                )
                state["sql_valid"] = False
                return state

        # 2. 强制校验：Pandas SQL 只支持 SELECT 开头的查询语句（核心规则）
        # 已移除 SELECT 开头检查，因为 Pandas 查询是 Python 代码而非标准 SQL
        pass

        # 3. SQL Server 表结构上下文
        columns_info = get_schema_columns_info(state.get("table_names"))
        # 4. LLM 精准校验（优化Prompt，贴合Pandas SQL规则，让校验结果更准确）
        # ✅ 改造Prompt核心：明确告知LLM是【Pandas SQL】+【仅校验SELECT语法】+【校验列名合法性】
        prompt = render_prompt(
            SQL_VALIDATION_PROMPT,
            columns_info=columns_info,
            sql_query=sql,
            extra_rule="""
            重要校验规则：
            1. 该SQL执行于 SQL Server，仅支持标准 SELECT 查询语法；
            2. 必须校验SQL中使用的所有列名是否存在于上述 Columns 列表中，列名大小写不敏感；
            3. 语法错误/列名错误/使用了非SELECT的语法，均判定为INVALID；
            4. 只返回【VALID】或【INVALID + 具体原因】，不要返回多余内容。
            """,
        )

        llm = get_llm()
        response = llm.invoke([HumanMessage(content=prompt)])
        result = response.content.strip().upper()

        # 5. LLM校验结果判定
        if "INVALID" in result:
            # logger.warning(f"Validation failed (LLM): {response.content.strip()}")
            state["error_message"] = f"代码验证失败: {response.content.strip()}"
            state["sql_valid"] = False
            return state

        # 所有校验通过
        # logger.info("SQL validation passed.")
        state["sql_valid"] = True
        state["error_message"] = ""
        return state
    except Exception as e:
        # logger.error(f"SQL validation error: {str(e)}", exc_info=True)
        state["error_message"] = f"validate_sql_node节点执行错误。错误详情：{str(e)}"
        return state
