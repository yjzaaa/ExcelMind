# 分摊 SQL 生成器模板（Python）

> 用于 Q3/Q4/Q7 类分摊场景的统一 SQL 生成。

```python
from typing import List

ALLOC_TEMPLATE = '''WITH monthly_alloc AS (
    SELECT
        cdb.[Year],
        COALESCE(SUM(CAST(cdb.[Amount] AS FLOAT)), 0) AS [Base_Month_Cost],
        COALESCE(SUM(CAST(cdb.[Amount] AS FLOAT) * COALESCE(
            CASE WHEN TRY_CAST(REPLACE(t7.[RateNo], '%', '') AS FLOAT) > 1
                 THEN TRY_CAST(REPLACE(t7.[RateNo], '%', '') AS FLOAT) / 100
                 ELSE TRY_CAST(REPLACE(t7.[RateNo], '%', '') AS FLOAT)
            END, 0)), 0) AS [Allocated_Month_Cost],
        {party_field} AS [Allocated_Party]
    FROM SSME_FI_InsightBot_CostDataBase cdb
    LEFT JOIN SSME_FI_InsightBot_Rate t7
        ON cdb.[Year] = t7.[Year]
       AND cdb.[Scenario] = t7.[Scenario]
       AND cdb.[Key] = t7.[Key]
       AND cdb.[Month] = t7.[Month]
    WHERE {year_filter}
      AND {scenario_filter}
      AND cdb.[Function] = {function_literal}
      AND {party_filter}
    GROUP BY cdb.[Year], {party_field}
),
yearly_agg AS (
    SELECT
        [Year],
        [Allocated_Party],
        SUM([Allocated_Month_Cost]) AS [Year_Allocated_Cost]
    FROM monthly_alloc
    GROUP BY [Year], [Allocated_Party]
),
compare AS (
    SELECT
        [Allocated_Party],
        [Year],
        [Year_Allocated_Cost],
        LAG([Year_Allocated_Cost]) OVER (PARTITION BY [Allocated_Party] ORDER BY [Year]) AS [Prev_Allocated_Cost]
    FROM yearly_agg
)
SELECT
    [Allocated_Party],
    [Year],
    [Year_Allocated_Cost],
    CASE WHEN [Prev_Allocated_Cost] IS NULL THEN NULL ELSE [Year_Allocated_Cost] - [Prev_Allocated_Cost] END AS [Allocated_Cost_Diff],
    CASE WHEN [Prev_Allocated_Cost] IS NULL OR [Prev_Allocated_Cost] = 0 THEN 0
         ELSE ROUND((([Year_Allocated_Cost] / [Prev_Allocated_Cost]) - 1) * 100, 2) END AS [Allocated_Cost_Diff_Rate(%)
    ]
FROM compare
ORDER BY [Allocated_Party], [Year] DESC;'''


def _quote_literal(s: str) -> str:
    return "'{}'".format(s.replace("'", "''"))


def _build_or_list(items: List[str], field_name: str) -> str:
    if not items:
        return '1=1'
    lits = [_quote_literal(i) for i in items]
    if len(lits) == 1:
        return f"{field_name} = {lits[0]}"
    return '(' + ' OR '.join([f"{field_name} = {v}" for v in lits]) + ')'


def generate_alloc_sql(
    years: List[str],
    scenarios: List[str],
    function_name: str,
    party_field: str,
    party_value: str,
) -> str:
    year_filter = _build_or_list(years, 'cdb.[Year]')
    scenario_filter = _build_or_list(scenarios, 'cdb.[Scenario]')
    function_literal = _quote_literal(function_name)
    party_filter = f"{party_field} = {party_value}"
    return ALLOC_TEMPLATE.format(
        party_field=party_field,
        year_filter=year_filter,
        scenario_filter=scenario_filter,
        function_literal=function_literal,
        party_filter=party_filter,
    )
```
