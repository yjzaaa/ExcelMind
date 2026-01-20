import pandas as pd
import os
import sys

# FIX: Bypass proxy for localhost to avoid 502 errors with LM Studio/Ollama
os.environ["NO_PROXY"] = "localhost,127.0.0.1"

from excel_agent.tools import _calculate_allocated_costs_impl,execute_pandas_query,_df_to_result
from excel_agent.excel_loader import get_loader
from excel_agent.graph import generate_sql_node, analyze_intent_node, AgentState
from excel_agent.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

#  pd.merge(cdb, t7, 
#                         on=['Month', 'Year', 'Scenario', 'Key'], 
#                         how='left') \
#                 .assign(rate=lambda x: x['Value'].fillna(0)) \
#                 .groupby(['Month', 'Amount'], as_index=False) \
#                 .agg(rate=('rate', 'sum')) \
#                 .sort_values('Month')
def load_real_data():
    file_path = r"D:\FI\FI\back_end_code\Data\Function cost allocation analysis to IT 20260104.xlsx"

    if not os.path.exists(file_path):
        print(f"❌ Error: File not found at {file_path}")
        return

    print(f"📂 Loading file: {file_path}")

    try:
        loader = get_loader()
        # 2. Load Sheets
        print("   Loading 'CostDataBase'...")
        loader.add_table(file_path, sheet_name="CostDataBase")

        loader.add_table(file_path, sheet_name="Table7")
      
    except Exception as e:
        print(f"❌ Error loading sheets: {e}")
        return


def test_node():
    print("🚀 Starting Allocation Logic Test with REAL DATA")
    print("-------------------------------------------------------")
    # 3. Test the node
    print("\n-------------------------------------------------------")
    print("🔄 Executing Node Logic Test")
    load_real_data()
    try:
        # AgentState is a TypedDict, so we initialize it as a dict
        # state = {
        #     "user_query": "IT cost 有哪些服务",
        #     "messages": [],
        #     "intent_analysis": None,
        #     "sql_query": None,
        #     "sql_valid": False,
        #     "execution_result": None,
        #     "error_message": None,
        #     "retry_count": 0,
        # }

        # # Step 1: Analyze Intent
        # print("\n1. Analyzing Intent...")
        # state = analyze_intent_node(state)
        # print(f"Intent Analysis Result: {state.get('intent_analysis')}")

        # # Step 2: Generate SQL
        # print("\n2. Generating SQL...")
        # state = generate_sql_node(state)

        # # logger.info(state)
        # print("\nGenerated SQL:")
        # print(state["sql_query"])

        # {"target": "CT", "target_type": "BL", "year": "FY25", "scenario": "Actual", "function": "HR"}
        loader = get_loader()
        # logger.info(loader.get_all_tables_field_values_json()) 
        # 优化后的查询语句
        query = """pd.merge(CostDataBase, Table7, on=['Month', 'Year', 'Scenario', 'Key'], how='left').assign(rate=lambda x: x['RateNo'].fillna(0)).groupby(['Month', 'Amount'], as_index=False).agg(rate=('rate', 'sum')).sort_values('Month')
        """

        # 执行查询
        result_df = execute_pandas_query(query)
        logger.info(result_df)
        # _calculate_allocated_costs_impl(target="CT",target_type="BL",year="FY25",scenario="Actual",function="HR Allocation")
    except Exception as e:
        print(f"❌ Error during node execution: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # 1. Define File Path
    # file_path = r"D:\AI_Python\AI2\AI2\back_end_code\Data\Function cost allocation analysis to IT 20260104.xlsx"

    # if not os.path.exists(file_path):
    #     print(f"❌ Error: File not found at {file_path}")

    # print(f"📂 Loading file: {file_path}")

    # try:
    #     loader = get_loader()
    #     # 2. Load Sheets
    #     print("   Loading 'CostDataBase'...")
    #     loader.add_table(file_path, sheet_name="CostDataBase")

    #     loader.add_table(file_path, sheet_name="Table7")

    # except Exception as e:
    #     print(f"❌ Error loading sheets: {e}")

    # print(
    #     _calculate_allocated_costs_impl(
    #         target_bl="CT", year="FY25", scenario="Actual", function="HR Allocation"
    #     )
    # )

    test_node()
