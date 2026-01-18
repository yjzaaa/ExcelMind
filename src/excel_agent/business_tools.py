
from typing import Any, Dict, Optional, List
import pandas as pd
from langchain_core.tools import tool
from .excel_loader import get_loader
from .tools import _df_to_result

@tool
def get_service_details(
    function: str,
    year: Optional[str] = None,
    scenario: Optional[str] = None
) -> Dict[str, Any]:
    """查询特定功能部门（Function）在指定年份提供的服务内容明细。
    
    该函数会查询 CostDataBase 表，根据 Function、Year 和 Scenario 进行筛选，
    并返回去重后的 Cost text 和 Key 信息，用于回答“某部门的费用包含哪些服务”类的问题。

    Args:
        function: 功能部门名称，例如 "IT", "HR", "Procurement"。
        year: 财年，例如 "FY25", "FY26"。如果不提供，则不按年份筛选（通常建议提供）。
        scenario: 场景，例如 "Actual", "Budget"。如果不提供，则不按场景筛选。

    Returns:
        包含服务内容（Cost text）和代码（Key）的列表。
    """
    loader = get_loader()
    tables = loader.get_loaded_dataframes()
    
    cdb = tables.get("CostDataBase")
    if cdb is None:
        return {"error": "未找到 CostDataBase 表，请先加载数据。"}

    # 构建查询条件
    query_parts = [f"Function == '{function}'"]
    
    if year:
        query_parts.append(f"Year == '{year}'")
    
    if scenario:
        query_parts.append(f"Scenario == '{scenario}'")
        
    query_str = " and ".join(query_parts)
    
    try:
        filtered_df = cdb.query(query_str)
        
        # 提取相关列并去重
        # 假设主要关注 'Cost text' 和 'Key'，如果还有其他描述性字段也可以加上
        # 根据之前的日志，列名有 ['BL', 'CC', 'Year', 'Scenario', 'Month', 'Key', 'Function', 'Cost text', 'Account', 'Category', 'Amount']
        target_cols = ['Cost text', 'Key']
        # 确保列存在
        available_cols = [c for c in target_cols if c in filtered_df.columns]
        
        if not available_cols:
             return {"error": f"CostDataBase 中未找到目标列 {target_cols}"}

        result_df = filtered_df[available_cols].drop_duplicates()
        
        return _df_to_result(result_df)
        
    except Exception as e:
        return {"error": f"查询服务明细出错: {str(e)}"}
