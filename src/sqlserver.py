"""SQL Server 数据源支持"""

from __future__ import annotations

import os
from typing import List, Optional

import pandas as pd
import pyodbc

from excel_agent.logger import get_logger


logger = get_logger("sqlserver")


def parse_table_list(raw: Optional[str]) -> List[str]:
    """解析逗号分隔的表名列表"""
    if not raw:
        return []
    return [t.strip() for t in raw.split(",") if t.strip()]


def get_tables_from_env() -> List[str]:
    """从环境变量读取表列表（由调用方决定是否使用）"""
    raw = os.getenv("SQLSERVER_TABLES", "").strip()
    return parse_table_list(raw)


def _resolve_driver(driver_name: str) -> str:
    drivers = pyodbc.drivers()
    if not drivers:
        return driver_name

    if driver_name in drivers:
        return driver_name

    # 常见别名映射
    if driver_name.lower() in {"microsoft sql server", "sql server"}:
        for candidate in reversed(drivers):
            if "sql server" in candidate.lower():
                return candidate

    # 兜底：选择已安装的最新 SQL Server 驱动
    for candidate in reversed(drivers):
        if "sql server" in candidate.lower():
            return candidate

    return driver_name


def _build_connection_string() -> str:
    """基于环境变量构建连接字符串"""
    explicit = os.getenv("SQLSERVER_CONNECTION_STRING")
    if explicit:
        return explicit

    host = os.getenv("SQLSERVER_HOST") or os.getenv("database_url")
    port = os.getenv("SQLSERVER_PORT") or os.getenv("database_port", "1433")
    database = os.getenv("SQLSERVER_DATABASE") or os.getenv("database_name")
    user = os.getenv("SQLSERVER_USER") or os.getenv("database_username")
    password = os.getenv("SQLSERVER_PASSWORD") or os.getenv("database_password")
    driver = os.getenv("SQLSERVER_DRIVER") or os.getenv(
        "database_driver", "ODBC Driver 18 for SQL Server"
    )
    driver = _resolve_driver(driver)
    encrypt = os.getenv("SQLSERVER_ENCRYPT", "yes")
    trust_cert = os.getenv("SQLSERVER_TRUST_SERVER_CERT", "yes")
    timeout = os.getenv("SQLSERVER_TIMEOUT", "30")

    if not host or not database:
        raise ValueError(
            "SQL Server 配置缺失：请设置 SQLSERVER_HOST 与 SQLSERVER_DATABASE"
        )

    server = f"{host},{port}" if port else host
    auth = "Trusted_Connection=yes;" if not user else f"UID={user};PWD={password};"

    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"{auth}"
        f"Encrypt={encrypt};"
        f"TrustServerCertificate={trust_cert};"
        f"Connection Timeout={timeout};"
    )


def _connect() -> pyodbc.Connection:
    conn_str = _build_connection_string()
    return pyodbc.connect(conn_str)


def execute_sql_query(sql: str) -> pd.DataFrame:
    """执行 SQL 并返回 DataFrame"""
    logger.info("Executing SQL Server query.")
    with _connect() as conn:
        return pd.read_sql_query(sql, conn)


def get_schema_context(tables: Optional[List[str]] = None) -> str:
    """获取 SQL Server 表结构上下文（用于提示词与上下文替换）"""
    if not tables:
        return "未提供表名列表，请由 agent 节点传入 tables。"
    table_list = ", ".join([f"'{t}'" for t in tables])
    sql = (
        "SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE "
        "FROM INFORMATION_SCHEMA.COLUMNS "
        f"WHERE TABLE_NAME IN ({table_list}) "
        "ORDER BY TABLE_NAME, ORDINAL_POSITION"
    )
    df = execute_sql_query(sql)
    if df.empty:
        return "未能从 SQL Server 获取表结构。"

    lines = ["📊 **已连接 SQL Server 数据源**", "", "**表结构**:"]
    for table_name in tables:
        sub = df[df["TABLE_NAME"] == table_name]
        if sub.empty:
            continue
        cols = [f"[{r.COLUMN_NAME}] ({r.DATA_TYPE})" for r in sub.itertuples()]
        lines.append(f"- {table_name}: " + ", ".join(cols))
    return "\n".join(lines)


def get_schema_columns_info(tables: Optional[List[str]] = None) -> str:
    """返回列信息字符串（用于 SQL 校验上下文）"""
    if not tables:
        return "Columns: (no tables provided)"
    table_list = ", ".join([f"'{t}'" for t in tables])
    sql = (
        "SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE "
        "FROM INFORMATION_SCHEMA.COLUMNS "
        f"WHERE TABLE_NAME IN ({table_list}) "
        "ORDER BY TABLE_NAME, ORDINAL_POSITION"
    )
    df = execute_sql_query(sql)
    if df.empty:
        return "Columns: (no columns found)"

    lines = ["Columns:"]
    for table_name in tables:
        sub = df[df["TABLE_NAME"] == table_name]
        if sub.empty:
            continue
        cols = [f"{r.COLUMN_NAME} ({r.DATA_TYPE})" for r in sub.itertuples()]
        lines.append(f"- {table_name}: " + ", ".join(cols))
    return "\n".join(lines)
