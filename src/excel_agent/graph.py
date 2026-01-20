"""LangGraph 工作流定义 - SQL 自修正闭环"""

from re import S
from turtle import st
from langchain_core.messages.base import BaseMessage
import pandas as pd

import operator
import json,os
from typing import Annotated, Any, Dict, List, Literal, TypedDict, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from .config import get_config
from .excel_loader import get_loader
from .prompts import (
    SYSTEM_PROMPT,
    INTENT_ANALYSIS_PROMPT,
    SQL_GENERATION_PROMPT,
    SQL_VALIDATION_PROMPT,
    ANSWER_REFINEMENT_PROMPT,
)
from .schemas import IntentAnalysisResult
from .tools import ALL_TOOLS, execute_pandas_query, calculate_allocated_costs
from .logger import RichConsoleCallbackHandler, get_logger
from .business_tools import get_service_details
from .knowledge_base import get_knowledge_base, format_knowledge_context
from .trace_store import TraceStore
from .cache import get_intent_cache, set_intent_cache, get_rag_cache, set_rag_cache
from langchain.chat_models import init_chat_model

logger = get_logger("excel_agent.graph")


import uuid
from datetime import datetime


class AgentState(TypedDict):
    """Agent 状态"""

    trace_id: Annotated[Optional[str], lambda x, y: y]  # 会话追踪 ID
    messages: Annotated[List[BaseMessage], add_messages]

    # 意图分析
    intent_analysis: Annotated[Any, lambda x, y: y]  # Optional[IntentAnalysisResult]
    knowledge_context: Annotated[str, lambda x, y: y]  # RAG 检索到的知识上下文
    all_tables_field_values:Annotated[str, lambda x, y: y]
    # SQL 流程状态
    user_query: Annotated[Optional[str], lambda x, y: y]
    sql_query: Annotated[Optional[str], lambda x, y: y]
    sql_valid: Annotated[bool, lambda x, y: y]
    execution_result: Annotated[
        Optional[str], lambda x, y: y
    ]  # 可能是 DataFrame string 或 error message

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


def get_llm():
    """获取 LLM 实例"""
    config = get_config()
    provider = config.model.get_active_provider()
    return init_chat_model(
                model=os.getenv("OPENAI_MODEL_ID"),
                model_provider=os.getenv("OPENAI_MODEL_PROVIDER"),
                base_url=os.getenv("OPENAI_BASE_URL"),
                api_version=os.getenv("OPENAI_API_VERSION"),
                api_key=os.getenv("OPENAI_API_KEY"),
                temperature=0.5
            )


    return ChatOpenAI(
        model=provider.model_name,
        api_key=provider.api_key,
        base_url=provider.base_url if provider.base_url else None,
        temperature=provider.temperature,
        max_tokens=provider.max_tokens,
    )


def load_context_node(state: AgentState) -> AgentState:
    """初始化上下文节点"""
    loader = get_loader()

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



    all_tables_field_values=loader.get_all_tables_field_values_json()
    knowledge_context=loader.get_active_loader().business_logic_context
    # 保存知识上下文到状态中
    state["knowledge_context"] = knowledge_context
    state["all_tables_field_values"]=all_tables_field_values
    state["user_query"] = user_query
    state["retry_count"] = retry_count
    state["error_message"] = state.get("error_message", "")  # 继承之前的错误（如果有）
    return state


def analyze_intent_node(state: AgentState) -> AgentState:
    """意图分析节点"""
    # 如果已经分析过，且不是重试循环中（通常意图分析只需做一次），则跳过
    # 但为了简单，我们先检查是否有 intent_analysis
    # if state.get("intent_analysis"):
    #     return {}

    # 修改：允许重新分析意图，特别是当出现参数错误时
    # 我们检查是否有错误信息，如果有，说明是重试，需要在 prompt 中加入错误上下文
    try:
        loader = get_loader()
        excel_summary = (
            loader.get_summary() if loader.is_loaded else "未加载 Excel 文件"
        )
        user_query = state.get("user_query", "")
        error_context = state.get("error_message", "")
       
        # 如果有错误上下文，且错误与参数缺失有关，提示 LLM 重新仔细提取参数
        additional_instruction = ""
        if error_context and (
            "target_bl" in error_context
            or "year" in error_context
            or "scenario" in error_context
            or "function" in error_context
        ):
            additional_instruction = f"\n\n⚠️ 上一次尝试失败，错误信息：{error_context}。\n请务必仔细检查用户问题，重新提取缺失的参数 (target_bl, year, scenario, function)。"

        prompt = (
            INTENT_ANALYSIS_PROMPT.format(
                excel_summary=excel_summary,
                user_query=user_query,
                knowledge_context=state["knowledge_context"],
                all_tables_field_values=state["all_tables_field_values"]
            )
            + additional_instruction
        )

        llm = get_llm()
        # structured_llm = llm.with_structured_output(IntentAnalysisResult)
        response = llm.invoke([HumanMessage(content=prompt)])
        state["intent_analysis"] = response

        # 写入意图缓存 (仅在成功且无错误时)
        # if not error_context:
        #     set_intent_cache(
        #         user_query,
        #         {"intent_analysis": response, "knowledge_context": knowledge_context},
        #         # context_hash,
        #     )

        return state
    except Exception as e:
        state["error_message"] = f"意图分析节点执行错误。错误详情：{str(e)}"
        return state


def generate_sql_node(state: AgentState) -> AgentState:
    try :
        """SQL 生成节点 (实际生成 Pandas 代码)"""
        loader = get_loader()
        excel_summary = loader.get_summary() if loader.is_loaded else "未加载 Excel 文件"

        user_query = state["user_query"]
        intent_analysis = state.get("intent_analysis", "")
        knowledge_context = state.get("knowledge_context", "暂无相关知识参考。")

        # 如果是 Pydantic 对象，转换为 JSON 字符串以便在 prompt 中使用
        if isinstance(intent_analysis, IntentAnalysisResult):
            intent_analysis = intent_analysis.model_dump_json(indent=2)

        error_context = state.get("error_message", "")

        if error_context:
            error_context = (
                f"上一次尝试失败，错误信息：{error_context}。请根据错误修正代码。"
            )

        # 检查是否应该直接调用 calculate_allocated_costs 工具
        # 虽然 prompt 已经鼓励 LLM 使用工具，但我们可以通过特定的提示强化这一点
        # 或者，我们可以在这里通过规则判断：如果用户意图明确是计算分摊，我们可以尝试直接生成工具调用代码

        all_tables_field_values=state["all_tables_field_values"]
        prompt = SQL_GENERATION_PROMPT.format(
            excel_summary=excel_summary,
            knowledge_context=knowledge_context,
            intent_analysis=intent_analysis,
            user_query=user_query,
            error_context=error_context,
            all_tables_field_values=all_tables_field_values
        )
        # logger.info(f"SQL prompt: {prompt}")
        llm = get_llm()

        # 获取所有可用的工具定义（为了让 LLM 知道有 get_service_details 等工具）
        tools = ALL_TOOLS

        # 使用 bind_tools 将工具信息传递给 LLM，允许它选择调用工具而不是生成代码
        llm_with_tools = llm.bind_tools(tools)

        # 使用 invoke 生成 SQL 或 工具调用
        response = llm_with_tools.invoke([HumanMessage(content=prompt)])

        # 检查是否有 tool_calls
        if response.tool_calls:
            # 如果 LLM 决定调用工具，我们将其转换为 JSON 格式的 tool_call 指令，
            # 以便 validate_sql_node 和 execute_sql_node 可以处理它。
            # 目前我们的架构期望 generate_sql_node 返回字符串（SQL 或 JSON 指令）。
            tool_call = response.tool_calls[0]
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # 构造 JSON 指令字符串
            import json

            sql = json.dumps(
                {"tool_call": tool_name, "parameters": tool_args}, ensure_ascii=False
            )
            # logger.info(f"LLM 选择调用工具: {tool_name}, 参数: {tool_args}")
        else:
            # 清理 markdown 标记
            sql = response.content.replace("```python", "").replace("```", "").strip()

        # logger.info(f"生成的 Pandas 代码: {sql}")
        state["sql_query"] = sql
        state["retry_count"] = state["retry_count"] + 1
        return state
    except Exception as e:
        state["error_message"] = f"enerate_sql节点执行错误。错误详情：{str(e)}"
        return state
    


def validate_sql_node(state: AgentState) -> AgentState:
    try:
        """SQL 验证节点（适配 Pandas SQL 只读查询规则，精准校验）"""
        sql = state["sql_query"]
        # 空SQL直接校验失败
        if not sql or sql.strip() == "":
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
                state["error_message"] = (
                    f"代码验证失败: 包含禁止的关键字 '{keyword}'。"
                    "请仅使用 Pandas 只读查询语法(SELECT)，禁止使用数据修改/文件读写/系统执行类语法。"
                )
                state["sql_valid"] = False
                return state

        # 2. 强制校验：Pandas SQL 只支持 SELECT 开头的查询语句（核心规则）
        # 已移除 SELECT 开头检查，因为 Pandas 查询是 Python 代码而非标准 SQL
        pass

        # 3. 表结构一致性硬校验（必须有，最核心的报错来源）
        loader = get_loader()
        active_loader = loader.get_active_loader()
        structure = (
            active_loader.get_structure()
            if active_loader and active_loader.is_loaded
            else {}
        )
        # 无表结构则跳过结构校验（避免无数据时报错）
        if not structure or "columns" not in structure or len(structure["columns"]) == 0:
            state["sql_valid"] = True
            state["error_message"] = ""
            return state

        # 提取当前数据表的【所有合法列名】和【字段类型】
        valid_column_names = [col["name"].lower() for col in structure.get("columns", [])]
        simple_columns = [
            f"{col['name']} ({col['dtype']})" for col in structure.get("columns", [])
        ]
        columns_info = f"Columns: {simple_columns}"
        all_tables_field_values=state["all_tables_field_values"]

        # 4. LLM 精准校验（优化Prompt，贴合Pandas SQL规则，让校验结果更准确）
        # ✅ 改造Prompt核心：明确告知LLM是【Pandas SQL】+【仅校验SELECT语法】+【校验列名合法性】
        prompt = SQL_VALIDATION_PROMPT.format(
            columns_info=columns_info,
            sql_query=sql,
            all_tables_field_values=all_tables_field_values,
            extra_rule="""
            重要校验规则：
            1. 该SQL是执行在Pandas DataFrame上的Pandas SQL语句，仅支持标准SELECT查询语法；
            2. 必须校验SQL中使用的所有列名是否存在于上述Columns列表中，列名大小写不敏感；
            3. 语法错误/列名错误/使用了非SELECT的语法，均判定为INVALID；
            4. 只返回【VALID】或【INVALID + 具体原因】，不要返回多余内容。
            """,
        )

        llm = get_llm()
        response = llm.invoke([HumanMessage(content=prompt)])
        result = response.content.strip().upper()

        # 5. LLM校验结果判定
        if "INVALID" in result:
            state["error_message"] = f"代码验证失败: {response.content.strip()}"
            state["sql_valid"] = False
            return state

        # 所有校验通过
        state["sql_valid"] = True
        state["error_message"] = ""
        return state
    except Exception as e:
        state["error_message"] = f"validate_sql_node节点执行错误。错误详情：{str(e)}"
        return state
    


def execute_sql_node(state: AgentState) -> AgentState:
    """SQL 执行节点 (实际执行 Pandas 或直接调用工具)"""
    sql = state["sql_query"]

    # 检查是否为工具调用指令 (JSON 格式)
    if sql.strip().startswith("{") and "tool_call" in sql:
        import json

        try:
            tool_data = json.loads(sql)
            tool_name = tool_data.get("tool_call")
            params = tool_data.get("parameters", {})

            # 查找对应工具
            target_tool = None
            for tool in ALL_TOOLS:
                if tool.name == tool_name:
                    target_tool = tool
                    break

            if target_tool:
                # logger.info(f"正在执行工具: {tool_name}, 参数: {params}")
                result = target_tool.invoke(params)

                # 处理工具返回结果
                if isinstance(result, dict) and "error" in result and result["error"]:
                    state["error_message"] = f"工具执行错误: {result['error']}"
                    return state

                state["execution_result"] = str(result)
                state["error_message"] = ""
                return state
            else:
                state["error_message"] = f"未找到工具: {tool_name}"
                return state

        except json.JSONDecodeError:
            pass  # 如果解析失败，尝试作为普通 SQL 执行
        except Exception as e:
            state["error_message"] = f"工具调用解析失败: {str(e)}"
            return state

    # 调用 tools.py 中的 execute_pandas_query
    # execute_pandas_query 是一个 StructuredTool 对象，需要调用其 invoke 方法
    result = execute_pandas_query.invoke({"query": sql})

    if "error" in result:
        # logger.warning(f"Pandas 执行出错: {result['error']}")
        state["error_message"] = f"执行出错: {result['error']}"
        return state

    result_str = str(result)
    # logger.info(f"Pandas 执行成功，结果长度: {len(result_str)}")
    state["execution_result"] = result_str
    state["error_message"] = ""
    return state  # 清除错误

def refine_answer_node(state: AgentState) -> AgentState:
    """生成最终回答节点"""
    user_query = state["user_query"]
    sql = state.get("sql_query", "未生成 SQL")
    execution_result = state.get("execution_result", "无结果")

    prompt = ANSWER_REFINEMENT_PROMPT.format(
        user_query=user_query, sql_query=sql, execution_result=execution_result
    )

    # 强化安全检查：如果执行结果包含错误，强制追加系统警告
    if (
        "error" in str(execution_result).lower()
        or "exception" in str(execution_result).lower()
    ):
        prompt += "\n\n⚠️ SYSTEM WARNING: 检测到执行结果包含错误信息。你必须停止尝试回答用户的问题数据。**绝对禁止**输出任何数据表格或数值。请仅解释错误原因。"

    llm = get_llm()
    response = llm.invoke([HumanMessage(content=prompt)])
    state["messages"] = [response]

    # 保存当前状态快照到 TraceStore
    if state.get("trace_id"):
        try:
            TraceStore.save_trace(state["trace_id"], state)
            # logger.info(f"Trace saved: {state['trace_id']}")
        except Exception as e:
            logger.warning(f"Failed to save trace: {e}")

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
) -> Literal["refine_answer", "analyze_intent", "generate_sql"]:
    """执行后的路由"""
    error = state.get("error_message", "")
    if not error:
        logger.info(f' route_after_execution not error retry_count{state["retry_count"]}')
        return "refine_answer"

    if state["retry_count"] >= 5:
        logger.info(f'route_after_execution retry_count{state["retry_count"]}')
        return "refine_answer"
    # 如果重试次数超过一定阈值（例如2次），且仍有错误，尝试重新分析意图
    # 这有助于处理因意图理解偏差导致的持续执行错误
    if state["retry_count"] > 2:
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
    # workflow.add_node("allocate_costs", allocate_costs_node)
    workflow.add_node("execute_sql", execute_sql_node)
    workflow.add_node("refine_answer", refine_answer_node)

    # 设置入口
    workflow.set_entry_point("load_context")

    # 边连接
    workflow.add_edge("load_context", "analyze_intent")


    workflow.add_edge("analyze_intent", "generate_sql")
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
