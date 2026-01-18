from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field


class AllocationParameters(BaseModel):
    """费用分摊参数"""

    target_bl: str = Field(..., description="目标业务线/部门，如 CT, DT")
    year: str = Field(..., description="财年，如 FY25")
    scenario: str = Field(..., description="场景，如 Actual, Budget")
    function: str = Field(..., description="功能/服务")


class IntentAnalysisResult(BaseModel):
    """意图分析结果"""

    intent_type: Literal["allocation", "general_query"] = Field(..., description="意图类型")
    next_step: Literal["allocate_costs", "generate_sql"] = Field(..., description="下一步操作")
    parameters: Optional[AllocationParameters] = Field(
        None, description="费用分摊参数，仅在 intent_type 为 allocation 时填充"
    )
    reasoning: str = Field(..., description="简要说明判断依据")
    field_mapping: Dict[str, str] = Field(default_factory=dict, description="字段名与含义的映射")

class SqlExecutionParams(BaseModel):
    """SQL 执行参数"""

    sql_query: str = Field(..., description="生成的 SQL 查询语句")
    execution_result: Optional[str] = Field(None, description="SQL 执行结果（DataFrame 字符串或错误信息）")
    
