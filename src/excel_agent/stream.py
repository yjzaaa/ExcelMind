"""流式对话 - 使用 LangChain ReAct Agent"""

import json
from typing import Any, AsyncGenerator, Dict

from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    AIMessageChunk,
    ToolMessage,
    BaseMessage,
)
from langchain_openai import ChatOpenAI
from .graph import get_graph  # 引入自定义图

from .config import get_config
from .excel_loader import get_loader
from .knowledge_base import get_knowledge_base, format_knowledge_context
from .tools import ALL_TOOLS
from .logger import RichConsoleCallbackHandler, get_logger

logger = get_logger("excel_agent.stream")


class CustomJSONEncoder(json.JSONEncoder):
    """自定义 JSON 编码器，处理 Pandas/Numpy 类型"""

    def default(self, obj):
        # 处理 Pandas Timestamp
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        # 处理 numpy 类型
        if hasattr(obj, "item"):
            return obj.item()
        # 处理 numpy 数组
        if hasattr(obj, "tolist"):
            return obj.tolist()
        # 处理 pandas NaT
        if str(obj) == "NaT":
            return None
        # 处理 pandas NA
        if str(obj) == "<NA>":
            return None
        return super().default(obj)


def json_dumps(obj, **kwargs):
    """使用自定义编码器的 JSON 序列化函数"""
    return json.dumps(obj, cls=CustomJSONEncoder, **kwargs)


SYSTEM_PROMPT = """你是一个专业的 Excel 数据分析助手。

## 当前 Excel 信息
{excel_summary}

## 相关知识参考
{knowledge_context}

## 工作原则
1. 根据用户问题，判断是否需要使用工具
2. 如需工具，调用合适的工具获取数据
3. 工具调用成功后，根据结果回答用户问题
4. **最终回答直接给出结论和分析**，不要描述"我使用了xx工具"或"我进行了xx操作"等内部过程
5. 回答语气友好，使用中文，并给出自己的一些数据分析建议
6. 如果有相关知识参考，请遵循其中的规则和建议
"""


async def stream_chat(
    message: str, history: list = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """执行对话 - 使用 LangChain ReAct Agent

    Args:
        message: 当前用户消息
        history: 历史对话列表，每项为 {"role": "user"|"assistant", "content": "..."}
    """
    loader = get_loader()

    if not loader.is_loaded:
        yield {"type": "error", "content": "请先上传 Excel 文件"}
        return

    try:
        # 获取当前活跃表ID
        active_table_id = loader.active_table_id
        active_table_info = loader.get_active_table_info()
        current_table_name = (
            active_table_info.filename if active_table_info else "未知表"
        )

        # 主对话开始
        yield {"type": "thinking", "content": "正在处理请求..."}

        # 准备输入消息
        current_message = f"[当前操作表: {current_table_name}] {message}"
        messages = []

        # 添加历史对话
        if history:
            for msg in history:
                if msg.get("role") == "user":
                    messages.append(HumanMessage(content=msg.get("content", "")))
                elif msg.get("role") == "assistant":
                    messages.append(AIMessage(content=msg.get("content", "")))

        messages.append(HumanMessage(content=current_message))

        # 获取自定义图
        graph = get_graph()

        # 准备输入状态
        input_state = {
            "messages": messages,
            "is_relevant": True,  # 默认假设相关，或者让 intent 节点去判断
        }

        # 使用 astream_events 获取细粒度事件
        # 记录状态
        thinking_done_sent = False
        final_answer_started = False
        trace_id = None

        # 增加 recursion_limit 以防止复杂任务或多次重试导致图执行中断
        config = {"recursion_limit": 14}

        async for event in graph.astream_events(
            input_state, version="v2", config=config
        ):
            kind = event["event"]

            # 1. 获取 Trace ID (在链结束或节点更新时)
            if kind == "on_chain_end":
                data = event.get("data", {})
                output = data.get("output")
                # 检查 output 是否是状态字典且包含 trace_id
                if isinstance(output, dict) and "trace_id" in output:
                    if not trace_id and output["trace_id"]:
                        trace_id = output["trace_id"]
                        yield {"type": "trace_info", "trace_id": trace_id}

            # 2. 获取思考过程 (RAG, Intent Analysis, SQL Generation 等节点的输出)
            # 我们可以监听特定节点的 on_chain_end
            if kind == "on_chain_end":
                name = event.get("name")
                if name == "analyze_intent_node":
                    yield {"type": "thinking", "content": "正在分析意图...\n"}
                elif name == "generate_sql_node":
                    yield {"type": "thinking", "content": "正在生成查询逻辑...\n"}
                elif name == "execute_sql_node":
                    yield {"type": "thinking", "content": "正在执行数据查询...\n"}

            # 3. 获取 LLM 流式 Token (最终回答)
            # 我们只关心 refine_answer_node 里的 LLM 输出，或者最后的回答
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    if not thinking_done_sent:
                        yield {"type": "thinking_done"}
                        thinking_done_sent = True

                    yield {"type": "token", "content": content}

            # 4. 错误处理
            if kind == "on_chain_error":
                logger.error(f"Chain Error: {event}")

        yield {"type": "done", "content": ""}

    except Exception as e:
        import traceback

        logger.error(f"Stream processing failed: {str(e)}", exc_info=True)
        # traceback.print_exc() # 使用 logger 替代直接打印
        yield {"type": "thinking_done"}
        yield {"type": "error", "content": f"处理出错: {str(e)}"}
