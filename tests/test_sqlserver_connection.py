import os
import pytest
import pyodbc

from sqlserver import execute_sql_query, _build_connection_string


def _has_sqlserver_config() -> bool:
    return bool(
        os.getenv("SQLSERVER_CONNECTION_STRING")
        or (
            (os.getenv("SQLSERVER_HOST") or os.getenv("database_url"))
            and (os.getenv("SQLSERVER_DATABASE") or os.getenv("database_name"))
        )
    )


def test_sqlserver_connection():
    if not _has_sqlserver_config():
        pytest.skip("SQL Server 配置缺失，跳过连接性测试")

    drivers = pyodbc.drivers()
    if not any("sql server" in d.lower() for d in drivers):
        pytest.skip("未检测到 SQL Server ODBC 驱动，跳过连接性测试")

    # 构造连接字符串（验证环境变量完整性）
    conn_str = _build_connection_string()
    assert conn_str

    # 简单连通性测试
    df = execute_sql_query("SELECT 1 AS ok")
    assert not df.empty
    assert df.iloc[0]["ok"] == 1
