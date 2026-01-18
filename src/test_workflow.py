import asyncio
import pandas as pd
from langchain_core.messages import HumanMessage
from excel_agent.graph import get_graph
from excel_agent.excel_loader import get_loader

# 模拟数据
def setup_mock_data():
    loader = get_loader()
    
    # 1. 模拟主数据 CostDataBase
    data = {
        "Year": ["FY26", "FY26", "FY25", "FY26"],
        "Scenario": ["Budget1", "Budget1", "Actual", "Budget1"],
        "Function": ["HR", "IT", "IT", "Finance"],
        "Amount": [1000, 2000, 1500, 3000],
        "Month": ["Oct", "Nov", "Oct", "Dec"],
        "cost text": ["Training", "Server Maintenance", "Laptop", "Audit"],
        "Allocation Key": ["Headcount", "Usage", "Usage", "Revenue"]
    }
    df = pd.DataFrame(data)
    
    # 手动注入到 loader 中（绕过文件读取）
    loader._tables["mock_table"] = type('MockLoader', (), {"dataframe": df, "is_loaded": True})()
    # 还需要 hack 一下 get_table 方法等，或者更简单地，直接覆盖 _df
    # 为了让 loader 正常工作，我们需要模拟得更像一点
    
    # 创建一个真实的 ExcelLoader 实例并填充数据
    from excel_agent.excel_loader import ExcelLoader
    mock_loader = ExcelLoader()
    mock_loader._df = df
    mock_loader._file_path = "mock_data.xlsx"
    mock_loader._sheet_name = "CostDataBase"
    mock_loader._all_sheets = ["CostDataBase", "解释和逻辑", "问题"]
    
    # 注入上下文
    mock_loader.business_logic_context = """
    ## 业务解释和逻辑
    - FY26 代表 2026 财年
    - Budget1 代表第一次预算
    - Cost text 代表具体的费用项描述
    - Allocation Key 代表分摊给业务部门的依据
    """
    
    # 注册到 MultiExcelLoader
    loader._tables["mock_id"] = mock_loader
    loader._active_table_id = "mock_id"
    
    # Mock list_tables 用于 execute_sql
    loader._table_infos["mock_id"] = type('MockInfo', (), {
        "id": "mock_id", 
        "filename": "mock_data.xlsx",
        "sheet_name": "CostDataBase"
    })()
    
    print("✅ 模拟数据加载完成")

async def test_workflow():
    setup_mock_data()
    
    graph = get_graph()
    
    # 测试问题：包含业务术语和字段查询
    query = "26财年IT费用的服务内容有哪些？以及它们是按什么分摊的？"
    print(f"\n🔍 测试问题: {query}")
    print("-" * 50)
    
    inputs = {"messages": [HumanMessage(content=query)]}
    
    print("🚀 开始执行工作流...")
    async for event in graph.astream(inputs):
        for key, value in event.items():
            print(f"\n📍 节点: {key}")
            if key == "analyze_intent":
                print(f"   意图分析: {value.get('intent_analysis')[:100]}...")
            elif key == "generate_sql":
                print(f"   生成 SQL: {value.get('sql_query')}")
            elif key == "validate_sql":
                valid = value.get('sql_valid')
                print(f"   验证结果: {'✅ 通过' if valid else '❌ 失败'}")
                if not valid:
                    print(f"   错误信息: {value.get('error_message')}")
            elif key == "execute_sql":
                result = value.get('execution_result')
                print(f"   执行结果预览: {result[:200] if result else 'None'}...")
            elif key == "refine_answer":
                print(f"   最终回答: {value.get('messages')[0].content}")
                
    print("-" * 50)
    print("✅ 测试完成")

if __name__ == "__main__":
    asyncio.run(test_workflow())
