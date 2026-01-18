import asyncio
import os

# 强制禁用本地代理，解决 Ollama 502 错误
os.environ["NO_PROXY"] = "localhost,127.0.0.1"

from langchain_core.messages import HumanMessage
from excel_agent.graph import get_graph
from excel_agent.allocationagent import run_allocation_agent

from excel_agent.excel_loader import get_loader
from excel_agent.logger import setup_logging, get_logger
from dotenv import load_dotenv

from langgraph.errors import GraphRecursionError

# 配置日志
setup_logging()
logger = get_logger("analysis_runner")


async def run_analysis():
    # 1. 设置文件路径
    file_path = r"D:\AI_Python\AI2\AI2\back_end_code\Data\Function cost allocation analysis to IT 20260104.xlsx"
    load_dotenv()
    logger.info(f"📂 正在加载数据文件: {file_path}")

    try:
        # 2. 加载 Excel 文件
        loader = get_loader()
        # 注意：这里我们加载默认的 sheet，loader 会自动寻找并读取 "解释和逻辑" 和 "问题" sheet
        # 我们显式指定加载 'CostDataBase' Sheet，因为这才是我们要分析的数据
        table_id, structure = loader.add_table(file_path, sheet_name="CostDataBase")
        table7_id, table7_structure = loader.add_table(file_path, sheet_name="Table7")

        logger.info(f"✅ 数据加载成功! Table ID: {table_id}  Table7 ID: {table7_id}")
        logger.info(
            f"   当前分析的主数据 Sheet: {structure['sheet_name']}  Table7 Sheet: {table7_structure['sheet_name']}"
        )
        logger.info(
            f"   所有发现的 Sheet: {structure['all_sheets']}  Table7 Sheets: {table7_structure['all_sheets']}"
        )
        logger.info(
            f"   数据规模: {structure['total_rows']} 行, {structure['total_columns']} 列  Table7 数据规模: {table7_structure['total_rows']} 行, {table7_structure['total_columns']} 列"
        )

        # 打印一下加载到的上下文，确认是否读取成功
        active_loader = loader.get_active_loader()
        if active_loader.business_logic_context:
            logger.info("\n📚 [自动识别] 成功读取 '解释和逻辑' Sheet 作为业务上下文")
            # logger.info(active_loader.business_logic_context[:200] + "...")
        else:
            logger.warning("\n⚠️ 未检测到 '解释和逻辑' Sheet 或内容为空")

        if active_loader.common_questions_context:
            logger.info("❓ [自动识别] 成功读取 '问题' Sheet 作为常见问题参考")

    except Exception as e:
        logger.error(f"❌ 加载文件失败: {e}")
        return

    # 3. 准备查询
    # query = "IT费用都有些什么服务，这些服务是按什么分摊给业务部门的？"
    # query = "How does Procurement Cost change from FY25 Actual to FY26 BGT？"
    # query = "What was the actual  HR cost allocated to CT in FY25?"
    # query = "26财年采购的预算费用和25财年实际数比，变化是什么？"
    query = "What services do IT cost service include? "
    logger.info(f"\n🔍 用户问题: {query}")
    logger.info("-" * 50)

    # 4. 运行工作流
    # graph = run_allocation_agent() # This is wrong, run_allocation_agent expects a query string
    from excel_agent.graph import get_graph

    graph = get_graph()

    inputs = {"messages": [HumanMessage(content=query)]}

    logger.info("🚀 开始执行工作流...")
    try:
        async for event in graph.astream(inputs, config={"recursion_limit": 15}):
            for key, value in event.items():

                if key == "analyze_intent":
                    if value.get("error_message"):
                        logger.error(
                            f" analyze_intent  执行错误: {value.get('error_message')}"
                        )
                    else:
                        logger.info(f"   意图分析: {value.get('intent_analysis')}...")

                elif key == "generate_sql":
                    if value.get("retry_count", 0) > 0:
                        logger.info(f"   (重试次数: {value.get('retry_count')})")
                    elif value.get("error_message"):
                        logger.error(
                            f" generate_sql  执行错误: {value.get('error_message')}"
                        )
                    elif value.get("sql_query"):
                        logger.info(f"   生成 SQL: {value.get('sql_query')}")

                elif key == "validate_sql":
                    valid = value.get("sql_valid")
                    if not valid:
                        logger.warning(
                            f" validate_sql  错误信息: {value.get('error_message')}"
                        )
                    else:
                        logger.info(f"   验证结果: {'✅ 通过' if valid else '❌ 失败'}")

                elif key == "execute_sql":
                    result = value.get("execution_result")
                    # 截断过长的结果显示
                    display_result = (
                        result[:300] + "..." if result and len(result) > 300 else result
                    )
                    if value.get("error_message"):
                        logger.error(
                            f"  execute_sql 执行错误: {value.get('error_message')}"
                        )
                    elif display_result:
                        logger.info(f"   执行结果: {display_result}")
                elif key == "allocate_costs":
                    result = value.get("execution_result")
                    # 截断过长的结果显示
                    display_result = (
                        result[:500] + "..." if result and len(result) > 500 else result
                    )
                    if value.get("retry_count", 0) > 0:
                        logger.warning(f"(重试次数: {value.get('retry_count')})")
                    if value.get("error_message"):
                        logger.error(
                            f"allocate_costs  执行错误: {value.get('error_message')}"
                        )
                    elif value.get("error_message") == "":
                        logger.info(f"   成本分配结果: {display_result}")

                elif key == "refine_answer":
                    logger.info("-" * 50)
                    # logger.info(f"   意图分析: {value}")
                    logger.info(f"📝 最终回答:\n{value.get('messages')[0].content}")
                    return value.get("messages")[0].content

            logger.info("-" * 50)
            logger.info(f"{key} ✅ 分析完成")
    except GraphRecursionError:
        logger.error(
            "❌ 工作流执行达到最大递归深度，强制终止。这通常是因为陷入了死循环。"
        )
    except Exception as e:
        logger.error(f"❌ 工作流执行发生未捕获异常: {e}")


if __name__ == "__main__":
    asyncio.run(run_analysis())
