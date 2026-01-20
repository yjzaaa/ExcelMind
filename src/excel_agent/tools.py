"""Excel 操作工具集"""

from math import cos
from typing import Any, Dict, List, Optional

import pandas as pd
from langchain_core.tools import tool

from .excel_loader import get_loader
from .config import get_config
from .logger import get_logger

logger = get_logger("excel_agent.tools")


def _limit_result(df: pd.DataFrame, limit: Optional[int] = None) -> pd.DataFrame:
    """限制返回结果行数"""
    config = get_config()
    if limit is None:
        limit = config.excel.default_result_limit
    limit = min(limit, config.excel.max_result_limit)
    return df.head(limit)


def _df_to_result(
    df: pd.DataFrame,
    limit: Optional[int] = None,
    select_columns: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """将 DataFrame 转换为结果字典"""
    if select_columns:
        # 确保请求的列存在
        available_cols = [c for c in select_columns if c in df.columns]
        if available_cols:
            df = df[available_cols]

    limited_df = _limit_result(df, limit)
    return {
        "total_rows": len(df),
        "returned_rows": len(limited_df),
        "columns": list(limited_df.columns),
        "data": limited_df.to_dict(orient="records"),
    }


def _get_filter_mask(
    df: pd.DataFrame, column: str, operator: str, value: Any
) -> pd.Series:
    """内部辅助函数：生成单个筛选条件的布尔掩码"""
    if column not in df.columns:
        raise ValueError(f"列 '{column}' 不存在，可用列: {list(df.columns)}")

    col = df[column]

    # 尝试将 value 转换为数值进行比较
    try:
        numeric_value = float(value)
    except (ValueError, TypeError):
        numeric_value = None

    compare_value = numeric_value if numeric_value is not None else value

    if operator == "==":
        return col == compare_value
    elif operator == "!=":
        return col != compare_value
    elif operator == ">":
        return col > compare_value
    elif operator == "<":
        return col < compare_value
    elif operator == ">=":
        return col >= compare_value
    elif operator == "<=":
        return col <= compare_value
    elif operator == "contains":
        return col.astype(str).str.contains(str(value), case=False, na=False)
    elif operator == "startswith":
        return col.astype(str).str.startswith(str(value), na=False)
    elif operator == "endswith":
        return col.astype(str).str.endswith(str(value), na=False)
    else:
        raise ValueError(f"不支持的运算符: {operator}")


@tool
def filter_data(
    column: Optional[str] = None,
    operator: Optional[str] = None,
    value: Optional[Any] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    select_columns: Optional[List[str]] = None,
    sort_by: Optional[str] = None,
    ascending: bool = True,
    limit: int = 20,
) -> Dict[str, Any]:
    """按条件筛选 Excel 数据，支持排序。

    Args:
        column: 单条件筛选时的列名
        operator: 比较运算符，仅支持: ==, !=, >, <, >=, <=, contains, startswith, endswith
                  注意: 不支持 between/equals 等运算符，请用多个 >= 和 <= 条件代替 between
        value: 单条件筛选时的比较值（支持字符串、数值等任意类型）
        filters: 多条件筛选列表，每个元素为 {"column": "...", "operator": "...", "value": ...}
                 operator 同样仅支持上述列出的运算符
        select_columns: 指定返回的列名列表，为空则返回所有列
        sort_by: 排序列名，可选
        ascending: 排序方向，True为升序，False为降序，默认True
        limit: 返回结果数量限制，默认20

    Returns:
        筛选后的数据（可选排序）
    """
    loader = get_loader()
    df = loader.dataframe.copy()

    try:
        # 初始掩码为全 True
        final_mask = pd.Series([True] * len(df))

        # 1. 处理单条件参数 (兼容旧调用)
        if column and operator and value is not None:
            mask = _get_filter_mask(df, column, operator, value)
            final_mask &= mask

        # 2. 处理多条件列表
        if filters:
            for f in filters:
                f_col = f.get("column")
                f_op = f.get("operator")
                f_val = f.get("value")
                if f_col and f_op and f_val is not None:
                    mask = _get_filter_mask(df, f_col, f_op, f_val)
                    final_mask &= mask

        result_df = df[final_mask]

        # 3. 排序（如果指定了 sort_by）
        if sort_by:
            if sort_by not in result_df.columns:
                return {
                    "error": f"排序列 '{sort_by}' 不存在，可用列: {list(result_df.columns)}"
                }
            result_df = result_df.sort_values(by=sort_by, ascending=ascending)

        return _df_to_result(result_df, limit, select_columns)
    except Exception as e:
        return {"error": f"筛选出错: {str(e)}"}


@tool
def aggregate_data(
    column: str, agg_func: str, filters: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """对指定列进行聚合统计。可选先筛选数据再聚合。

    Args:
        column: 要统计的列名
        agg_func: 聚合函数，可选值: sum, mean, count, min, max, median, std
        filters: 可选的筛选条件列表，每个元素为 {"column": "...", "operator": "...", "value": ...}
                 operator 仅支持: ==, !=, >, <, >=, <=, contains, startswith, endswith
                 注意: 不支持 between/equals，用 >= 和 <= 组合代替

    Returns:
        统计结果
    """
    loader = get_loader()
    df = loader.dataframe.copy()

    # 如果有筛选条件，先进行筛选
    if filters:
        try:
            final_mask = pd.Series([True] * len(df))
            for f in filters:
                f_col = f.get("column")
                f_op = f.get("operator")
                f_val = f.get("value")
                if f_col and f_op and f_val is not None:
                    mask = _get_filter_mask(df, f_col, f_op, f_val)
                    final_mask &= mask
            df = df[final_mask]
        except Exception as e:
            return {"error": f"筛选条件错误: {str(e)}"}

    if column not in df.columns:
        return {"error": f"列 '{column}' 不存在，可用列: {list(df.columns)}"}

    col = df[column]

    try:
        if agg_func == "sum":
            result = col.sum()
        elif agg_func == "mean":
            result = col.mean()
        elif agg_func == "count":
            result = col.count()
        elif agg_func == "min":
            result = col.min()
        elif agg_func == "max":
            result = col.max()
        elif agg_func == "median":
            result = col.median()
        elif agg_func == "std":
            result = col.std()
        else:
            return {"error": f"不支持的聚合函数: {agg_func}"}

        # 处理 numpy 类型
        if hasattr(result, "item"):
            result = result.item()

        return {
            "column": column,
            "function": agg_func,
            "filtered_rows": len(df),
            "result": result,
        }
    except Exception as e:
        return {"error": f"聚合计算出错: {str(e)}"}


@tool
def group_and_aggregate(
    group_by: str,
    agg_column: str,
    agg_func: str,
    filters: Optional[List[Dict[str, Any]]] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """按列分组并进行聚合统计。可选先筛选数据再分组。

    Args:
        group_by: 分组列名
        agg_column: 要聚合的列名
        agg_func: 聚合函数，可选值: sum, mean, count, min, max
        filters: 可选的筛选条件列表，operator 仅支持: ==, !=, >, <, >=, <=, contains, startswith, endswith
        limit: 返回结果数量限制，默认20

    Returns:
        分组聚合结果
    """
    loader = get_loader()
    df = loader.dataframe.copy()

    # 如果有筛选条件，先进行筛选
    if filters:
        try:
            final_mask = pd.Series([True] * len(df))
            for f in filters:
                f_col = f.get("column")
                f_op = f.get("operator")
                f_val = f.get("value")
                if f_col and f_op and f_val is not None:
                    mask = _get_filter_mask(df, f_col, f_op, f_val)
                    final_mask &= mask
            df = df[final_mask]
        except Exception as e:
            return {"error": f"筛选条件错误: {str(e)}"}

    if group_by not in df.columns:
        return {"error": f"分组列 '{group_by}' 不存在，可用列: {list(df.columns)}"}
    if agg_column not in df.columns:
        return {"error": f"聚合列 '{agg_column}' 不存在，可用列: {list(df.columns)}"}

    try:
        grouped = df.groupby(group_by)[agg_column].agg(agg_func).reset_index()
        grouped.columns = [group_by, f"{agg_column}_{agg_func}"]

        # 按聚合结果降序排序
        grouped = grouped.sort_values(by=grouped.columns[1], ascending=False)

        result = _df_to_result(grouped, limit)
        result["filtered_rows"] = len(df)
        return result
    except Exception as e:
        return {"error": f"分组聚合出错: {str(e)}"}


@tool
def sort_data(
    column: str,
    ascending: bool = True,
    filters: Optional[List[Dict[str, Any]]] = None,
    select_columns: Optional[List[str]] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """按指定列排序数据。可选先筛选、指定返回列。

    Args:
        column: 排序列名
        ascending: 是否升序排列，默认True
        filters: 可选的筛选条件列表
        select_columns: 指定返回的列名列表
        limit: 返回结果数量限制，默认20

    Returns:
        排序后的数据
    """
    loader = get_loader()
    df = loader.dataframe.copy()

    # 如果有筛选条件，先进行筛选
    if filters:
        try:
            final_mask = pd.Series([True] * len(df))
            for f in filters:
                f_col = f.get("column")
                f_op = f.get("operator")
                f_val = f.get("value")
                if f_col and f_op and f_val is not None:
                    mask = _get_filter_mask(df, f_col, f_op, f_val)
                    final_mask &= mask
            df = df[final_mask]
        except Exception as e:
            return {"error": f"筛选条件错误: {str(e)}"}

    if column not in df.columns:
        return {"error": f"列 '{column}' 不存在，可用列: {list(df.columns)}"}

    try:
        sorted_df = df.sort_values(by=column, ascending=ascending)
        return _df_to_result(sorted_df, limit, select_columns)
    except Exception as e:
        return {"error": f"排序出错: {str(e)}"}


@tool
def search_data(
    keyword: str,
    columns: Optional[List[str]] = None,
    select_columns: Optional[List[str]] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """在指定列或所有列中搜索关键词。

    Args:
        keyword: 搜索关键词
        columns: 要搜索的列名列表，为空则搜索所有列
        select_columns: 指定返回的列名列表
        limit: 返回结果数量限制，默认20

    Returns:
        包含关键词的数据行
    """
    loader = get_loader()
    df = loader.dataframe

    try:
        # 确定搜索范围
        search_cols = columns if columns else df.columns

        # 在指定列中搜索
        mask = pd.Series([False] * len(df))
        for col in search_cols:
            if col in df.columns:
                mask |= df[col].astype(str).str.contains(keyword, case=False, na=False)

        result_df = df[mask]
        return _df_to_result(result_df, limit, select_columns)
    except Exception as e:
        return {"error": f"搜索出错: {str(e)}"}


@tool
def get_column_stats(
    column: str, filters: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """获取指定列的详细统计信息。可选先筛选数据再统计。

    Args:
        column: 列名
        filters: 可选的筛选条件列表

    Returns:
        列的统计信息
    """
    loader = get_loader()
    df = loader.dataframe.copy()

    # 如果有筛选条件，先进行筛选
    if filters:
        try:
            final_mask = pd.Series([True] * len(df))
            for f in filters:
                f_col = f.get("column")
                f_op = f.get("operator")
                f_val = f.get("value")
                if f_col and f_op and f_val is not None:
                    mask = _get_filter_mask(df, f_col, f_op, f_val)
                    final_mask &= mask
            df = df[final_mask]
        except Exception as e:
            return {"error": f"筛选条件错误: {str(e)}"}

    if column not in df.columns:
        return {"error": f"列 '{column}' 不存在，可用列: {list(df.columns)}"}

    col = df[column]

    try:
        stats = {
            "column": column,
            "filtered_rows": len(df),
            "dtype": str(col.dtype),
            "count": int(col.count()),
            "null_count": int(col.isna().sum()),
            "unique_count": int(col.nunique()),
        }

        # 数值类型额外统计
        if pd.api.types.is_numeric_dtype(col):
            stats.update(
                {
                    "min": float(col.min()) if not col.isna().all() else None,
                    "max": float(col.max()) if not col.isna().all() else None,
                    "mean": float(col.mean()) if not col.isna().all() else None,
                    "median": float(col.median()) if not col.isna().all() else None,
                }
            )

        return stats
    except Exception as e:
        return {"error": f"统计出错: {str(e)}"}


@tool
def get_unique_values(
    column: str, filters: Optional[List[Dict[str, Any]]] = None, limit: int = 50
) -> Dict[str, Any]:
    """获取指定列的唯一值列表。可选先筛选数据。

    Args:
        column: 列名
        filters: 可选的筛选条件列表
        limit: 返回唯一值数量限制，默认50

    Returns:
        唯一值列表及其计数
    """
    loader = get_loader()
    df = loader.dataframe.copy()

    # 如果有筛选条件，先进行筛选
    if filters:
        try:
            final_mask = pd.Series([True] * len(df))
            for f in filters:
                f_col = f.get("column")
                f_op = f.get("operator")
                f_val = f.get("value")
                if f_col and f_op and f_val is not None:
                    mask = _get_filter_mask(df, f_col, f_op, f_val)
                    final_mask &= mask
            df = df[final_mask]
        except Exception as e:
            return {"error": f"筛选条件错误: {str(e)}"}

    if column not in df.columns:
        return {"error": f"列 '{column}' 不存在，可用列: {list(df.columns)}"}

    try:
        value_counts = df[column].value_counts()
        total_unique = len(value_counts)

        if limit:
            value_counts = value_counts.head(limit)

        values = [
            {"value": str(idx), "count": int(count)}
            for idx, count in value_counts.items()
        ]

        return {
            "column": column,
            "filtered_rows": len(df),
            "total_unique": total_unique,
            "returned_unique": len(values),
            "values": values,
        }
    except Exception as e:
        return {"error": f"获取唯一值出错: {str(e)}"}


@tool
def get_data_preview(n_rows: int = 10) -> Dict[str, Any]:
    """获取数据预览。

    Args:
        n_rows: 预览行数，默认10行

    Returns:
        数据预览
    """
    loader = get_loader()
    active_loader = loader.get_active_loader()
    if active_loader is None:
        return {"error": "没有活跃的表"}
    return active_loader.get_preview(n_rows)


@tool
def get_current_time() -> Dict[str, Any]:
    """获取当前系统时间。

    Returns:
        当前时间信息
    """
    from datetime import datetime

    now = datetime.now()
    return {
        "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "weekday": now.strftime("%A"),
        "timestamp": now.timestamp(),
    }


@tool
def calculate(expressions: List[str]) -> Dict[str, Any]:
    """执行数学计算。

    Args:
        expressions: 数学表达式列表，例如 ["(100+200)*0.5", "500/2"]

    Returns:
        每个表达式的计算结果
    """
    import math

    results = {}

    # 定义安全的计算环境
    safe_env = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "pow": pow,
        "math": math,
    }

    for expr in expressions:
        try:
            # 移除危险字符，防止恶意代码
            if any(char in expr for char in ["__", "import", "eval", "exec", "open"]):
                results[expr] = "Error: Unsafe expression"
                continue

            # 执行计算
            result = eval(expr, {"__builtins__": None}, safe_env)
            results[expr] = result
        except Exception as e:
            results[expr] = f"Error: {str(e)}"

    return {"results": results}


@tool
def generate_chart(
    chart_type: Optional[str] = None,
    x_column: Optional[str] = None,
    y_column: Optional[str] = None,
    agg_column: Optional[str] = None,  # y_column 的别名，用于饼图等分组聚合场景
    group_by: Optional[str] = None,
    agg_func: str = "sum",
    title: str = "",
    filters: Optional[List[Dict[str, Any]]] = None,
    series_columns: Optional[List[str]] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """生成 ECharts 可视化图表配置。

    Args:
        chart_type: 图表类型，可选: bar(柱状图), line(折线图), pie(饼图),
                   scatter(散点图), radar(雷达图), funnel(漏斗图)。
                   为空或"auto"时自动推荐。
        x_column: X轴数据列名（分类轴）
        y_column: Y轴数据列名（数值轴，单系列时使用）
        agg_column: 聚合列名（y_column 的别名，用于饼图等场景）
        group_by: 分组列名（用于饼图和多系列图）
        agg_func: 聚合函数: sum, mean, count, min, max
        title: 图表标题
        filters: 筛选条件列表，operator 仅支持: ==, !=, >, <, >=, <=, contains, startswith, endswith
                 注意: 不支持 between/equals，请用 >= 和 <= 组合代替 between
        series_columns: 多系列Y轴列名列表
        limit: 数据点数量限制，默认20

    Returns:
        包含 ECharts 配置的字典 {"chart": {...}, "message": "..."}
    """
    # 处理 agg_column 作为 y_column 的别名
    if agg_column and not y_column:
        y_column = agg_column

    loader = get_loader()
    df = loader.dataframe.copy()

    # 应用筛选条件
    if filters:
        try:
            final_mask = pd.Series([True] * len(df))
            for f in filters:
                f_col = f.get("column")
                f_op = f.get("operator")
                f_val = f.get("value")
                if f_col and f_op and f_val is not None:
                    mask = _get_filter_mask(df, f_col, f_op, f_val)
                    final_mask &= mask
            df = df[final_mask]
        except Exception as e:
            return {"error": f"筛选条件错误: {str(e)}"}

    if len(df) == 0:
        return {"error": "筛选后无数据，无法生成图表"}

    # 自动推荐图表类型
    def recommend_chart_type() -> str:
        """根据数据特征推荐图表类型"""
        if group_by and y_column:
            # 分组场景：检查分组数量
            unique_groups = df[group_by].nunique() if group_by in df.columns else 0
            if unique_groups <= 8:
                return "pie"  # 少量分组适合饼图
            return "bar"  # 多分组适合柱状图

        if x_column and y_column:
            x_dtype = df[x_column].dtype if x_column in df.columns else None
            y_dtype = df[y_column].dtype if y_column in df.columns else None

            # 两个数值列 → 散点图
            if pd.api.types.is_numeric_dtype(x_dtype) and pd.api.types.is_numeric_dtype(
                y_dtype
            ):
                return "scatter"

            # X轴是日期/时间类型 → 折线图
            if pd.api.types.is_datetime64_any_dtype(x_dtype):
                return "line"

            # 默认柱状图
            return "bar"

        # 仅有分组列 → 饼图
        if group_by:
            return "pie"

        return "bar"

    # 确定图表类型
    final_chart_type = (
        chart_type if chart_type and chart_type != "auto" else recommend_chart_type()
    )

    try:
        # 准备图表数据
        chart_data = _prepare_chart_data(
            df,
            final_chart_type,
            x_column,
            y_column,
            group_by,
            agg_func,
            series_columns,
            limit,
        )

        if "error" in chart_data:
            return chart_data

        # 生成 ECharts 配置
        chart_config = _build_echart_config(final_chart_type, chart_data, title)

        chart_type_names = {
            "bar": "柱状图",
            "line": "折线图",
            "pie": "饼图",
            "scatter": "散点图",
            "radar": "雷达图",
            "funnel": "漏斗图",
        }
        message = f"已生成{chart_type_names.get(final_chart_type, final_chart_type)}，共 {chart_data.get('data_count', 0)} 个数据点。"

        return {
            "chart": chart_config,
            "chart_type": final_chart_type,
            "message": message,
        }
    except Exception as e:
        return {"error": f"生成图表出错: {str(e)}"}


def _prepare_chart_data(
    df: pd.DataFrame,
    chart_type: str,
    x_column: Optional[str],
    y_column: Optional[str],
    group_by: Optional[str],
    agg_func: str,
    series_columns: Optional[List[str]],
    limit: int,
) -> Dict[str, Any]:
    """准备图表数据"""

    if chart_type == "pie":
        # 饼图：按分组列聚合
        if group_by and group_by in df.columns:
            if y_column and y_column in df.columns:
                grouped = df.groupby(group_by)[y_column].agg(agg_func).reset_index()
                grouped.columns = ["name", "value"]
            else:
                grouped = df[group_by].value_counts().reset_index()
                grouped.columns = ["name", "value"]

            grouped = grouped.head(limit)
            data = [
                {"name": str(row["name"]), "value": float(row["value"])}
                for _, row in grouped.iterrows()
            ]
            return {"data": data, "data_count": len(data)}
        else:
            return {"error": "饼图需要指定 group_by 分组列"}

    elif chart_type == "scatter":
        # 散点图：需要两个数值列
        if not x_column or not y_column:
            return {"error": "散点图需要指定 x_column 和 y_column"}
        if x_column not in df.columns or y_column not in df.columns:
            return {"error": f"列不存在: {x_column} 或 {y_column}"}

        scatter_df = (
            df[[x_column, y_column]].dropna().head(limit * 5)
        )  # 散点图可以多一些点
        data = scatter_df.values.tolist()
        return {
            "data": data,
            "x_name": x_column,
            "y_name": y_column,
            "data_count": len(data),
        }

    elif chart_type == "radar":
        # 雷达图：多个指标对比
        if not series_columns or len(series_columns) < 3:
            return {"error": "雷达图需要至少3个 series_columns 指标列"}

        valid_cols = [
            c
            for c in series_columns
            if c in df.columns and pd.api.types.is_numeric_dtype(df[c])
        ]
        if len(valid_cols) < 3:
            return {"error": "雷达图需要至少3个有效的数值列"}

        # 计算每个指标的聚合值
        if group_by and group_by in df.columns:
            # 按分组生成多个雷达系列
            grouped = df.groupby(group_by)[valid_cols].agg(agg_func).head(limit)
            indicators = [
                {"name": col, "max": float(df[col].max() * 1.2)} for col in valid_cols
            ]
            series_data = []
            for name, row in grouped.iterrows():
                series_data.append(
                    {
                        "name": str(name),
                        "value": [float(row[col]) for col in valid_cols],
                    }
                )
            return {
                "indicators": indicators,
                "series": series_data,
                "data_count": len(series_data),
            }
        else:
            # 单系列雷达图
            indicators = [
                {"name": col, "max": float(df[col].max() * 1.2)} for col in valid_cols
            ]
            values = [float(df[col].agg(agg_func)) for col in valid_cols]
            return {
                "indicators": indicators,
                "series": [{"name": "数据", "value": values}],
                "data_count": 1,
            }

    elif chart_type == "funnel":
        # 漏斗图：类似饼图，按值降序排列
        if group_by and group_by in df.columns:
            if y_column and y_column in df.columns:
                grouped = df.groupby(group_by)[y_column].agg(agg_func).reset_index()
                grouped.columns = ["name", "value"]
            else:
                grouped = df[group_by].value_counts().reset_index()
                grouped.columns = ["name", "value"]

            grouped = grouped.sort_values("value", ascending=False).head(limit)
            data = [
                {"name": str(row["name"]), "value": float(row["value"])}
                for _, row in grouped.iterrows()
            ]
            return {"data": data, "data_count": len(data)}
        else:
            return {"error": "漏斗图需要指定 group_by 分组列"}

    else:
        # bar / line：分类 + 数值
        if not x_column:
            return {"error": f"{chart_type}图需要指定 x_column"}
        if x_column not in df.columns:
            return {"error": f"列 '{x_column}' 不存在"}

        # 多系列处理
        if series_columns:
            valid_series = [c for c in series_columns if c in df.columns]
            if not valid_series:
                return {"error": "series_columns 中没有有效的列"}

            # 按 x_column 分组，计算每个系列的聚合值
            grouped = df.groupby(x_column)[valid_series].agg(agg_func).head(limit)
            categories = [str(idx) for idx in grouped.index]
            series = [
                {"name": col, "data": grouped[col].tolist()} for col in valid_series
            ]
            return {
                "categories": categories,
                "series": series,
                "data_count": len(categories),
            }

        # 单系列处理
        if y_column and y_column in df.columns:
            grouped = df.groupby(x_column)[y_column].agg(agg_func).reset_index()
            grouped.columns = ["category", "value"]
            grouped = grouped.sort_values("value", ascending=False).head(limit)
            categories = [str(c) for c in grouped["category"]]
            values = grouped["value"].tolist()
        else:
            # 仅计数
            grouped = df[x_column].value_counts().head(limit)
            categories = [str(idx) for idx in grouped.index]
            values = grouped.values.tolist()

        return {
            "categories": categories,
            "values": values,
            "data_count": len(categories),
        }


def _build_echart_config(
    chart_type: str, data: Dict[str, Any], title: str
) -> Dict[str, Any]:
    """构建 ECharts 配置"""

    # 通用配置
    base_config = {
        "title": {"text": title, "left": "center", "textStyle": {"color": "#e5e7eb"}},
        "tooltip": {
            "trigger": "item" if chart_type in ["pie", "scatter", "funnel"] else "axis"
        },
        "backgroundColor": "transparent",
    }

    if chart_type == "pie":
        return {
            **base_config,
            "legend": {
                "orient": "vertical",
                "left": "left",
                "textStyle": {"color": "#9ca3af"},
            },
            "series": [
                {
                    "type": "pie",
                    "radius": ["40%", "70%"],
                    "avoidLabelOverlap": True,
                    "itemStyle": {
                        "borderRadius": 10,
                        "borderColor": "#1f2937",
                        "borderWidth": 2,
                    },
                    "label": {"color": "#e5e7eb"},
                    "emphasis": {
                        "label": {"show": True, "fontSize": 16, "fontWeight": "bold"}
                    },
                    "data": data["data"],
                }
            ],
        }

    elif chart_type == "scatter":
        return {
            **base_config,
            "xAxis": {
                "type": "value",
                "name": data.get("x_name", ""),
                "axisLabel": {"color": "#9ca3af"},
                "axisLine": {"lineStyle": {"color": "#4b5563"}},
            },
            "yAxis": {
                "type": "value",
                "name": data.get("y_name", ""),
                "axisLabel": {"color": "#9ca3af"},
                "axisLine": {"lineStyle": {"color": "#4b5563"}},
            },
            "series": [
                {
                    "type": "scatter",
                    "symbolSize": 10,
                    "data": data["data"],
                    "itemStyle": {"color": "#6366f1"},
                }
            ],
        }

    elif chart_type == "radar":
        return {
            **base_config,
            "legend": {
                "data": [s["name"] for s in data["series"]],
                "bottom": 0,
                "textStyle": {"color": "#9ca3af"},
            },
            "radar": {
                "indicator": data["indicators"],
                "axisName": {"color": "#9ca3af"},
                "splitLine": {"lineStyle": {"color": "#4b5563"}},
                "splitArea": {
                    "areaStyle": {
                        "color": ["rgba(99,102,241,0.1)", "rgba(99,102,241,0.05)"]
                    }
                },
            },
            "series": [{"type": "radar", "data": data["series"]}],
        }

    elif chart_type == "funnel":
        return {
            **base_config,
            "legend": {
                "data": [d["name"] for d in data["data"]],
                "bottom": 0,
                "textStyle": {"color": "#9ca3af"},
            },
            "series": [
                {
                    "type": "funnel",
                    "left": "10%",
                    "width": "80%",
                    "label": {"show": True, "position": "inside", "color": "#fff"},
                    "labelLine": {"show": False},
                    "itemStyle": {"borderColor": "#1f2937", "borderWidth": 1},
                    "emphasis": {"label": {"fontSize": 16}},
                    "data": data["data"],
                }
            ],
        }

    else:
        # bar / line
        config = {
            **base_config,
            "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
            "xAxis": {
                "type": "category",
                "data": data["categories"],
                "axisLabel": {
                    "color": "#9ca3af",
                    "rotate": 30 if len(data["categories"]) > 8 else 0,
                },
                "axisLine": {"lineStyle": {"color": "#4b5563"}},
            },
            "yAxis": {
                "type": "value",
                "axisLabel": {"color": "#9ca3af"},
                "axisLine": {"lineStyle": {"color": "#4b5563"}},
                "splitLine": {"lineStyle": {"color": "#374151"}},
            },
        }

        # 处理多系列
        if "series" in data:
            config["legend"] = {
                "data": [s["name"] for s in data["series"]],
                "bottom": 0,
                "textStyle": {"color": "#9ca3af"},
            }
            config["series"] = [
                {
                    "name": s["name"],
                    "type": chart_type,
                    "data": s["data"],
                    "smooth": chart_type == "line",
                }
                for s in data["series"]
            ]
        else:
            config["series"] = [
                {
                    "type": chart_type,
                    "data": data["values"],
                    "smooth": chart_type == "line",
                    "itemStyle": {"color": "#6366f1"},
                    "areaStyle": (
                        {"color": "rgba(99,102,241,0.2)"}
                        if chart_type == "line"
                        else None
                    ),
                }
            ]

        return config


def _calculate_allocated_costs_impl(
    target: str,
    target_type: str,
    year: str,
    scenario: str,
    function: Optional[str] = None,
) -> pd.DataFrame:
    """内部实现：计算分摊费用（支持 BL 和 CC）"""
    if not target or not target_type or not year or not scenario:
        raise ValueError("target, target_type, year, scenario 不能为空")
    if "Allocation" not in function:
        return {"error": f"function 中必须含有 Allocation"}
    loader = get_loader()
    tables = loader.get_loaded_dataframes()
    cdb = tables.get("CostDataBase")
    t7 = tables.get("Table7")

    if cdb is None or t7 is None:
        raise ValueError("未找到 CostDataBase 或 Table7 表")

    # 1. 筛选 CDB
    cdb_query = f"Year == '{year}' and Scenario == '{scenario}'"
    if function:
        cdb_query += f" and Function == '{function}'"
    cdb_filtered = cdb.query(cdb_query).copy()

    # 2. 筛选 T7
    # 根据 target_type (BL 或 CC) 动态构建查询
    if target_type.upper() == "BL":
        t7_query = f"Year == '{year}' and Scenario == '{scenario}' and BL == '{target}'"
    elif target_type.upper() == "CC":
        # CC 可能是数字，尝试转换
        try:
            target_cc = int(target)
            t7_query = (
                f"Year == '{year}' and Scenario == '{scenario}' and CC == {target_cc}"
            )
        except ValueError:
            t7_query = (
                f"Year == '{year}' and Scenario == '{scenario}' and CC == '{target}'"
            )
    else:
        raise ValueError(f"不支持的目标类型: {target_type}，仅支持 BL 或 CC")

    # logger.info(cdb_filtered)
    # 仅保留 CDB 中存在的 Key
    valid_keys = cdb_filtered["Key"].unique()
    t7_filtered = t7.query(t7_query).copy()
    t7_filtered = t7_filtered[t7_filtered["Key"].isin(valid_keys)]

    if len(t7_filtered) == 0:
        # 如果没有匹配的分摊记录，返回空结果
        return pd.DataFrame(columns=["Month", "Allocated_Amount"])

    # 3. 聚合 Rate
    rate_col = "RateNo" if "RateNo" in t7_filtered.columns else "Value"
    t7_agg = t7_filtered.groupby(["Month", "Key"])[rate_col].sum().reset_index()
    t7_agg = t7_agg.rename(columns={rate_col: "Agg_Rate"})

    # 4. Merge
    merged = pd.merge(cdb_filtered, t7_agg, on=["Month", "Key"], how="left")

    # 5. Calculate
    merged["Agg_Rate"] = merged["Agg_Rate"].fillna(0)
    # aggregate_data=merged["Agg_Rate"]
    # amount= merged["Amount"]
    merged["Allocated_Amount"] = merged["Amount"] * merged["Agg_Rate"]

    # 6. Aggregate
    result = merged.groupby("Month")["Allocated_Amount"].sum().reset_index()

    # 排序
    month_order = {
        "Oct": 1,
        "Nov": 2,
        "Dec": 3,
        "Jan": 4,
        "Feb": 5,
        "Mar": 6,
        "Apr": 7,
        "May": 8,
        "Jun": 9,
        "Jul": 10,
        "Aug": 11,
        "Sep": 12,
    }
    result["Month_Num"] = result["Month"].map(month_order)
    result = result.sort_values("Month_Num").drop(columns=["Month_Num"])

    return result


@tool
def calculate_allocated_costs(
    target: str,
    target_type: str,
    year: str,
    scenario: str,
    function: Optional[str] = None,
) -> Dict[str, Any]:
    """计算特定目标 (BL 或 CC) 在指定年份和场景下的分摊费用。

    Args:
        target: 目标名称 (如 "CT" 或 "413001")
        target_type: 目标类型 ("BL" 或 "CC")
        year: 年份 (如 "FY26")
        scenario: 场景 (如 "Budget1")
        function: 可选，筛选 CostDataBase 的 Function (如 "HR Allocation")

    Returns:
        按月汇总的分摊费用结果
    """
    if "Allocation" not in function:
        return {"error": f"function 中必须含有 Allocation"}
    try:
        df = _calculate_allocated_costs_impl(
            target, target_type, year, scenario, function
        )
        total = df["Allocated_Amount"].sum()
        result = _df_to_result(df)
        result["total_amount"] = total
        return result
    except Exception as e:
        return {"error": f"分摊计算出错: {str(e)}"}



@tool
def compare_allocated_costs(
    target1: str,
    target_type1: str,
    year1: str,
    scenario1: str,
    target2: str,
    target_type2: str,
    year2: str,
    scenario2: str,
    function: Optional[str] = None,
) -> Dict[str, Any]:
    """对比两个不同分摊场景的结果差异。
    支持不同目标(BL/CC)、不同年份、不同场景的交叉对比。

    Args:
        target1: 目标1名称
        target_type1: 目标1类型 ("BL" 或 "CC")
        year1: 年份1
        scenario1: 场景1
        target2: 目标2名称
        target_type2: 目标2类型 ("BL" 或 "CC")
        year2: 年份2
        scenario2: 场景2
        function: 可选，筛选 Function

    Returns:
        对比结果表
    """
    try:
        if target1 !=target2:
            return {"error": f"target1 必须与 target2相同"}
            # 分别计算两个场景的分摊
        df1 = _calculate_allocated_costs_impl(
            target1, target_type1, year1, scenario1, function
        )
        df2 = _calculate_allocated_costs_impl(
            target2, target_type2, year2, scenario2, function
        )

        amt1 = df1["Allocated_Amount"].sum()
        amt2 = df2["Allocated_Amount"].sum()

        diff = amt1 - amt2
        pct = (diff / amt2 * 100) if amt2 != 0 else 0

        return pd.DataFrame(
            {
                "Metric": ["Allocated Amount"],
                f"{year1} {scenario1} ({target1})": [amt1],
                f"{year2} {scenario2} ({target2})": [amt2],
                "Difference": [diff],
                "Pct_Change": [pct],
            }
        )

    except Exception as e:
        return {"error": f"分摊对比出错: {str(e)}"}


def _calculate_trend_impl(
    year: str, scenario: str, function: Optional[str] = None
) -> pd.DataFrame:
    """内部实现：计算成本趋势"""
    loader = get_loader()
    tables = loader.get_loaded_dataframes()
    cdb = tables.get("CostDataBase")

    if cdb is None:
        raise ValueError("未找到 CostDataBase 表")

    query = f"Year == '{year}' and Scenario == '{scenario}'"
    if function:
        query += f" and Function == '{function}'"

    df = cdb.query(query).copy()

    # 按月汇总
    result = df.groupby("Month")["Amount"].sum().reset_index()

    # 排序月份
    month_order = {
        "Oct": 1,
        "Nov": 2,
        "Dec": 3,
        "Jan": 4,
        "Feb": 5,
        "Mar": 6,
        "Apr": 7,
        "May": 8,
        "Jun": 9,
        "Jul": 10,
        "Aug": 11,
        "Sep": 12,
    }
    result["Month_Num"] = result["Month"].map(month_order)
    result = result.sort_values("Month_Num").drop(columns=["Month_Num"])

    # 计算环比增长率
    result["MoM_Growth"] = result["Amount"].pct_change() * 100

    return result


@tool
def calculate_trend(
    year: str, scenario: str, function: Optional[str] = None
) -> Dict[str, Any]:
    """计算指定年份和场景下的成本月度趋势及环比增长。

    Args:
        year: 年份 (如 FY24)
        scenario: 场景 (如 Actual)
        function: 可选，筛选 Function

    Returns:
        按月汇总的金额及环比增长率
    """
    try:
        df = _calculate_trend_impl(year, scenario, function)
        return _df_to_result(df)
    except Exception as e:
        return {"error": f"趋势计算出错: {str(e)}"}


def _analyze_cost_composition_impl(
    year: str, scenario: str, dimension: str = "Category"
) -> pd.DataFrame:
    """内部实现：分析成本构成"""
    loader = get_loader()
    tables = loader.get_loaded_dataframes()
    cdb = tables.get("CostDataBase")

    if cdb is None:
        raise ValueError("未找到 CostDataBase 表")

    if dimension not in cdb.columns:
        raise ValueError(f"维度 '{dimension}' 不存在")

    df = cdb.query(f"Year == '{year}' and Scenario == '{scenario}'").copy()

    # 按维度汇总
    result = df.groupby(dimension)["Amount"].sum().reset_index()

    # 计算占比
    total = result["Amount"].sum()
    result["Percentage"] = (result["Amount"] / total * 100).round(2)

    # 按金额降序排列
    result = result.sort_values("Amount", ascending=False)

    return result


@tool
def analyze_cost_composition(
    year: str, scenario: str, dimension: str = "Category"
) -> Dict[str, Any]:
    """分析指定年份和场景下的成本构成（按维度汇总并计算占比）。

    Args:
        year: 年份 (如 FY24)
        scenario: 场景 (如 Actual)
        dimension: 分析维度 (如 Category, Account, Function)，默认为 Category

    Returns:
        按维度汇总的金额及占比
    """
    try:
        df = _analyze_cost_composition_impl(year, scenario, dimension)
        return _df_to_result(df)
    except Exception as e:
        return {"error": f"构成分析出错: {str(e)}"}


def _compare_scenarios_impl(
    year1: str,
    scenario1: str,
    year2: str,
    scenario2: str,
    function: Optional[str] = None,
) -> pd.DataFrame:
    """内部实现：对比两个场景"""
    loader = get_loader()
    tables = loader.get_loaded_dataframes()
    cdb = tables.get("CostDataBase")

    if cdb is None:
        raise ValueError("未找到 CostDataBase 表")

    # 获取两个场景的数据
    def get_amount(y, s, f):
        query = f"Year == '{y}' and Scenario == '{s}'"
        if f:
            query += f" and Function == '{f}'"
        return cdb.query(query)["Amount"].sum()

    amount1 = get_amount(year1, scenario1, function)
    amount2 = get_amount(year2, scenario2, function)

    diff = amount1 - amount2
    pct_change = (diff / amount2 * 100) if amount2 != 0 else 0

    return pd.DataFrame(
        {
            "Metric": ["Amount"],
            f"{year1} {scenario1}": [amount1],
            f"{year2} {scenario2}": [amount2],
            "Difference": [diff],
            "Pct_Change": [pct_change],
        }
    )


@tool
def compare_scenarios(
    year1: str,
    scenario1: str,
    year2: str,
    scenario2: str,
    function: Optional[str] = None,
) -> Dict[str, Any]:
    """对比两个不同年份/场景的总金额差异。
    通常用于计算同比(YoY)或预算执行偏差(Budget vs Actual)。

    Args:
        year1: 目标年份 (如 FY26)
        scenario1: 目标场景 (如 Budget1)
        year2: 基准年份 (如 FY25)
        scenario2: 基准场景 (如 Actual)
        function: 可选，筛选 Function (如 Procurement)

    Returns:
        包含两个场景金额、差异值及百分比变化的表格
    """
    try:
        df = _compare_scenarios_impl(year1, scenario1, year2, scenario2, function)
        return _df_to_result(df)
    except Exception as e:
        return {"error": f"场景对比出错: {str(e)}"}


# @tool
def execute_pandas_query(query: str, limit: int = 100) -> Dict[str, Any]:
    """执行 Pandas 查询。

    支持 pandas 的 query() 方法语法，或者简单的 Python 表达式。
    当前活跃的表可以用 `df` 引用。

    Args:
        query: Pandas 查询字符串或 Python 表达式
               例如:
               - df.query("Year == 'FY26'")
               - df[df['Year'] == 'FY26'][['cost text', 'Allocation Key']]
               - df.groupby('Function')['Amount'].sum()
        limit: 返回结果数量限制，默认100

    Returns:
        查询结果
    """
    logger.info(f"正在执行工具: execute_pandas_query, query={query}")
    loader = get_loader()

    # # 获取当前活跃的表
    # active_loader = loader.get_active_loader()
    # if not active_loader or not active_loader.is_loaded:
    #     return {"error": "没有活跃的表"}

    # df = active_loader.dataframe

    # 安全检查：禁止危险操作
    dangerous_keywords = [
        "import",
        "eval",
        "exec",
        "open",
        "write",
        "delete",
        "os.",
        "sys.",
        "subprocess",
    ]
    for keyword in dangerous_keywords:
        if keyword in query:
            return {"error": f"错误：查询包含禁止的关键字 '{keyword}'"}

    try:
        # 获取所有表的数据框，支持多表查询
        # 变量名通常是文件名（无后缀）
        all_dfs = loader.get_loaded_dataframes()

        # 准备执行环境
        local_env = {"pd": pd}
        if all_dfs:
            for name, data in all_dfs.items():
                # 简单的变量名清理，确保可用
                safe_name = name.replace(" ", "_").replace("-", "_")
                local_env[safe_name] = data
                # 也尝试保留原名（如果也是合法的）
                local_env[name] = data

        try:
            # logger.info(f"正在执行查询: {query} local_env={local_env}")
            result = eval(query, {"__builtins__": None}, local_env)
        except SyntaxError:
            # 可能是多行代码或包含赋值
            # 尝试 exec
            # 为了捕获最后一行表达式的值，我们可以尝试将最后一行单独拿出来 eval，或者包装一下

            # 简单处理：执行代码，如果代码中定义了 'result' 变量，则返回它
            # 或者，我们可以尝试解析代码，找到最后一个表达式节点
            import ast

            tree = ast.parse(query)
            if not tree.body:
                return {"result": None}

            # 分离最后一条语句和前面的语句
            last_stmt = tree.body[-1]
            front_stmts = tree.body[:-1]

            # 执行前面的语句
            if front_stmts:
                exec(
                    compile(
                        ast.Module(body=front_stmts, type_ignores=[]),
                        filename="<string>",
                        mode="exec",
                    ),
                    {"__builtins__": None},
                    local_env,
                )

            # 处理最后一条语句
            if isinstance(last_stmt, ast.Expr):
                # 如果是表达式，eval 它并作为结果
                result = eval(
                    compile(
                        ast.Expression(body=last_stmt.value),
                        filename="<string>",
                        mode="eval",
                    ),
                    {"__builtins__": None},
                    local_env,
                )
            else:
                # 如果不是表达式（例如赋值），执行它，并返回 None (或者检查是否有 result 变量)
                exec(
                    compile(
                        ast.Module(body=[last_stmt], type_ignores=[]),
                        filename="<string>",
                        mode="exec",
                    ),
                    {"__builtins__": None},
                    local_env,
                )

        # 处理结果
        if isinstance(result, pd.DataFrame):
            return _df_to_result(result, limit)
        elif isinstance(result, pd.Series):
            return _df_to_result(result.to_frame(), limit)
        else:
            # 标量结果
            return {"result": result}

    except Exception as e:
        # logger.error(f"工具 execute_pandas_query 执行出错: {str(e)}")
        return {"error": f"Pandas 查询执行出错: {str(e)}"}


# 导出工具列表
ALL_TOOLS = [
    filter_data,
    aggregate_data,
    group_and_aggregate,
    # sort_data,  # 已合并到 filter_data
    search_data,
    get_column_stats,
    get_unique_values,
    get_data_preview,
    get_current_time,
    calculate,
    generate_chart,
    execute_pandas_query,
    calculate_allocated_costs,  # 新增工具
    # calculate_trend,
    analyze_cost_composition,
    compare_scenarios,
    compare_allocated_costs,
]
# from .business_tools import get_service_details

# ALL_TOOLS.append(get_service_details)
