from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from .config import get_config
from .tools import calculate_allocated_costs
from .logger import get_logger

logger = get_logger("excel_agent.allocation_agent")


def get_llm():
    """获取 LLM 实例"""
    config = get_config()
    provider = config.model.get_active_provider()
    return ChatOpenAI(
        model=provider.model_name,
        api_key=provider.api_key,
        base_url=provider.base_url if provider.base_url else None,
        temperature=0,  # Use 0 for more deterministic tool calling
        max_tokens=provider.max_tokens,
    )


def create_allocation_agent_graph():
    """创建费用分摊 Agent Graph"""
    llm = get_llm()
    tools = [calculate_allocated_costs]

    system_prompt = "你是一个专门负责计算费用分摊的助手。你的唯一任务是准确地调用 `calculate_allocated_costs` 工具来回答用户关于分摊费用的问题。请确保从用户的问题中提取正确的 target_bl (业务线), year (财年), scenario (场景) 和可选的 function。如果缺少信息，请根据上下文推断或请求用户提供。"

    graph = create_agent(model=llm, tools=tools, system_prompt=system_prompt)

    return graph


def run_allocation_agent(query: str):
    """运行费用分摊 Agent"""
    graph = create_allocation_agent_graph()
    logger.info(f"Running allocation agent with query: {query}")
    try:
        # Graph input expects a dict with "messages"
        inputs = {"messages": [HumanMessage(content=query)]}
        result = graph.invoke(inputs)

        # Result is the final state, which contains "messages"
        messages = result["messages"]
        last_message = messages[-1]
        return last_message.content
    except Exception as e:
        logger.error(f"Allocation agent failed: {e}")
        return f"Error: {str(e)}"
