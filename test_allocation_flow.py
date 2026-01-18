import pandas as pd
import sys
import os


# 模拟 Agent 的核心逻辑流
class MockAgentFlow:
    def __init__(self):
        self.state = {}
        # 加载真实数据
        file_path = r"D:\AI_Python\AI2\AI2\back_end_code\Data\Function cost allocation analysis to IT 20260104.xlsx"
        print(f"📂 Loading Real Data from: {file_path}")
        try:
            self.mock_cdb = pd.read_excel(file_path, sheet_name="CostDataBase")
            self.mock_t7 = pd.read_excel(file_path, sheet_name="Table7")
            print("   ✅ Data Loaded Successfully")
        except Exception as e:
            print(f"   ❌ Failed to load data: {e}")
            sys.exit(1)

    def load_context(self, query):
        print(f"🔹 [Step 1] Loading Context: '{query}'")
        self.state["user_query"] = query
        self.state["loaded_tables"] = {
            "CostDataBase": self.mock_cdb,
            "Table7": self.mock_t7,
        }
        return self.state

    def analyze_intent(self):
        print("🔹 [Step 2] Analyzing Intent...")
        query = self.state["user_query"]

        # 模拟 LLM 意图识别逻辑 (基于规则模拟)
        # 优先匹配复杂的对比意图
        if ("分摊" in query and ("变化" in query or "比" in query)) or (
            "分摊" in query and "和" in query and "相比" in query
        ):
            # 区分是 "分摊对比" 还是 "场景对比"
            # 如果包含具体的接收方 (如 413001, XP)，则是分摊对比
            if "413001" in query or "XP" in query:
                # 模拟 "26财年预算要分摊给413001...和25财年实际分摊给XP..."
                params = {
                    "target1": "413001" if "413001" in query else None,
                    "target_type1": "CC",  # 假设意图识别能识别出数字是 CC
                    "year1": "FY26" if "26财年" in query else None,
                    "scenario1": "Budget1" if "预算" in query else None,
                    "target2": "XP" if "XP" in query else None,
                    "target_type2": "BL",  # 假设意图识别能识别出 XP 是 BL
                    "year2": "FY25" if "25财年" in query else None,
                    "scenario2": "Actual" if "实际" in query else None,
                    "function": "HR" if "HR" in query else None,
                }
                self.state["intent_analysis"] = {
                    "intent": "compare_allocated_costs",
                    "parameters": params,
                }
                print(f"   ✅ Intent Identified: compare_allocated_costs")
                print(f"   ✅ Parameters Extracted: {params}")
            else:
                self.state["intent_analysis"] = {"intent": "general_query"}
                print(
                    "   ℹ️ Intent Identified: general_query (Matched comparison but no targets found)"
                )

        elif "分摊" in query or "Allocation" in query:
            # 模拟提取参数 (更新为真实数据中存在的值)
            # CT 是存在的 BL，Actual 是存在的 Scenario
            params = {
                "target_bl": "CT" if "CT" in query else None,
                "year": "FY24" if "2024" in query else None,
                "scenario": "Actual" if "Actual" in query else None,
                "function": "IT Allocation" if "IT Allocation" in query else None,
            }

            self.state["intent_analysis"] = {
                "intent": "allocate_costs",
                "parameters": params,
            }
            print(f"   ✅ Intent Identified: allocate_costs")
            print(f"   ✅ Parameters Extracted: {params}")

        # 扩展意图识别
        elif "趋势" in query or "Trend" in query:
            params = {
                "year": "FY24" if "2024" in query else None,
                "scenario": "Actual" if "Actual" in query else None,
                "function": "HR" if "HR" in query else None,
            }
            self.state["intent_analysis"] = {
                "intent": "calculate_trend",
                "parameters": params,
            }
            print(f"   ✅ Intent Identified: calculate_trend")
            print(f"   ✅ Parameters Extracted: {params}")

        elif "构成" in query or "Composition" in query:
            params = {
                "year": "FY24" if "2024" in query else None,
                "scenario": "Actual" if "Actual" in query else None,
                "dimension": "Category",  # 默认
            }
            self.state["intent_analysis"] = {
                "intent": "analyze_cost_composition",
                "parameters": params,
            }
            print(f"   ✅ Intent Identified: analyze_cost_composition")
            print(f"   ✅ Parameters Extracted: {params}")

        elif "变化" in query or "比" in query:
            # 场景对比
            params = {
                "year1": "FY26" if "26财年" in query else None,
                "scenario1": "Budget1" if "预算" in query else None,
                "year2": "FY25" if "25财年" in query else None,
                "scenario2": "Actual" if "实际" in query else None,
                "function": "Procurement" if "采购" in query else None,
            }
            self.state["intent_analysis"] = {
                "intent": "compare_scenarios",
                "parameters": params,
            }
            print(f"   ✅ Intent Identified: compare_scenarios")
            print(f"   ✅ Parameters Extracted: {params}")
        else:
            self.state["intent_analysis"] = {"intent": "general_query"}
            print("   ℹ️ Intent Identified: general_query")

        return self.state

    def route(self):
        print("🔹 [Step 3] Routing...")
        intent = self.state.get("intent_analysis", {}).get("intent")
        if intent == "allocate_costs":
            return self.allocate_costs()
        elif intent == "calculate_trend":
            return self.calculate_trend()
        elif intent == "analyze_cost_composition":
            return self.analyze_cost_composition()
        elif intent == "compare_scenarios":
            return self.compare_scenarios()
        elif intent == "compare_allocated_costs":
            return self.compare_allocated_costs()
        else:
            return self.generate_sql()

    def compare_allocated_costs(self):
        print("🔹 [Step 4] Executing Allocation Comparison (Tool Call)...")
        params = self.state["intent_analysis"]["parameters"]

        # 复用 _calculate_allocated_costs_impl 逻辑 (这里简单模拟，实际上工具内部会调用)
        # 为了测试脚本简洁，我直接在这里实现精简版逻辑，或者如果我能 import tools 里的函数最好
        # 但考虑到环境隔离，我将在 MockAgentFlow 里实现类似逻辑

        cdb = self.state["loaded_tables"]["CostDataBase"]
        t7 = self.state["loaded_tables"]["Table7"]

        def calc_one(target, t_type, y, s, func):
            # 1. CDB
            q_cdb = f"Year == '{y}' and Scenario == '{s}'"
            if func:
                q_cdb += f" and Function == '{func}'"
            df_cdb = cdb.query(q_cdb)

            # 2. T7
            if t_type == "BL":
                q_t7 = f"Year == '{y}' and Scenario == '{s}' and BL == '{target}'"
            else:  # CC
                # 尝试转int
                try:
                    tgt = int(target)
                    q_t7 = f"Year == '{y}' and Scenario == '{s}' and CC == {tgt}"
                except:
                    q_t7 = f"Year == '{y}' and Scenario == '{s}' and CC == '{target}'"

            valid_keys = df_cdb["Key"].unique()
            df_t7 = t7.query(q_t7)
            df_t7 = df_t7[df_t7["Key"].isin(valid_keys)]

            # 3. Agg Rate
            rate_col = "RateNo" if "RateNo" in df_t7.columns else "Value"
            df_agg = df_t7.groupby(["Month", "Key"])[rate_col].sum().reset_index()
            df_agg = df_agg.rename(columns={rate_col: "Agg_Rate"})

            # 4. Merge & Calc
            merged = pd.merge(df_cdb, df_agg, on=["Month", "Key"], how="left")
            merged["Allocated_Amount"] = merged["Amount"] * merged["Agg_Rate"].fillna(0)

            return merged["Allocated_Amount"].sum()

        amt1 = calc_one(
            params["target1"],
            params["target_type1"],
            params["year1"],
            params["scenario1"],
            params["function"],
        )
        amt2 = calc_one(
            params["target2"],
            params["target_type2"],
            params["year2"],
            params["scenario2"],
            params["function"],
        )

        diff = amt1 - amt2
        pct = (diff / amt2 * 100) if amt2 != 0 else 0

        result = pd.DataFrame(
            {
                "Metric": ["Allocated Amount"],
                f"{params['year1']} {params['scenario1']} ({params['target1']})": [
                    amt1
                ],
                f"{params['year2']} {params['scenario2']} ({params['target2']})": [
                    amt2
                ],
                "Difference": [diff],
                "Pct_Change": [pct],
            }
        )

        print("   ✅ Allocation Comparison Completed:")
        print(result)
        self.state["execution_result"] = result
        return result

    def compare_scenarios(self):
        print("🔹 [Step 4] Executing Scenario Comparison (Tool Call)...")
        params = self.state["intent_analysis"]["parameters"]
        y1, s1 = params["year1"], params["scenario1"]
        y2, s2 = params["year2"], params["scenario2"]
        func = params["function"]

        cdb = self.state["loaded_tables"]["CostDataBase"]

        def get_amount(y, s, f):
            q = f"Year == '{y}' and Scenario == '{s}'"
            if f:
                q += f" and Function == '{f}'"
            return cdb.query(q)["Amount"].sum()

        amt1 = get_amount(y1, s1, func)
        amt2 = get_amount(y2, s2, func)

        diff = amt1 - amt2
        pct = (diff / amt2 * 100) if amt2 != 0 else 0

        result = pd.DataFrame(
            {
                "Metric": ["Amount"],
                f"{y1} {s1}": [amt1],
                f"{y2} {s2}": [amt2],
                "Difference": [diff],
                "Pct_Change": [pct],
            }
        )

        print("   ✅ Comparison Completed:")
        print(result)
        self.state["execution_result"] = result
        return result

    def calculate_trend(self):
        print("🔹 [Step 4] Executing Trend Analysis (Tool Call)...")
        params = self.state["intent_analysis"]["parameters"]
        year = params["year"]
        scenario = params["scenario"]
        function = params["function"]

        cdb = self.state["loaded_tables"]["CostDataBase"]

        query = f"Year == '{year}' and Scenario == '{scenario}'"
        if function:
            query += f" and Function == '{function}'"

        df = cdb.query(query).copy()
        print(f"   Step 4.1 Filtered Rows: {len(df)}")

        result = df.groupby("Month")["Amount"].sum().reset_index()

        # Sort
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

        # MoM
        result["MoM_Growth"] = result["Amount"].pct_change() * 100

        print("   ✅ Trend Analysis Completed (First 5 rows):")
        print(result.head())
        self.state["execution_result"] = result
        return result

    def analyze_cost_composition(self):
        print("🔹 [Step 4] Executing Cost Composition (Tool Call)...")
        params = self.state["intent_analysis"]["parameters"]
        year = params["year"]
        scenario = params["scenario"]
        dimension = params["dimension"]

        cdb = self.state["loaded_tables"]["CostDataBase"]

        df = cdb.query(f"Year == '{year}' and Scenario == '{scenario}'").copy()
        print(f"   Step 4.1 Filtered Rows: {len(df)}")

        result = df.groupby(dimension)["Amount"].sum().reset_index()
        total = result["Amount"].sum()
        result["Percentage"] = (result["Amount"] / total * 100).round(2)
        result = result.sort_values("Amount", ascending=False)

        print("   ✅ Composition Analysis Completed (Top 5):")
        print(result.head())
        self.state["execution_result"] = result
        return result

    def allocate_costs(self):
        print("🔹 [Step 4] Executing Allocation Logic (Tool Call)...")
        params = self.state["intent_analysis"]["parameters"]

        # 检查参数完整性
        if not all(params.values()):
            print("   ❌ Missing Parameters!")
            return None

        # 模拟 _calculate_allocated_costs_impl 逻辑
        target_bl = params["target_bl"]
        year = params["year"]
        scenario = params["scenario"]
        function = params["function"]

        cdb = self.state["loaded_tables"]["CostDataBase"]
        t7 = self.state["loaded_tables"]["Table7"]

        # 1. 筛选 CDB
        cdb_filtered = cdb[
            (cdb["Year"] == year)
            & (cdb["Scenario"] == scenario)
            & (cdb["Function"] == function)
        ].copy()
        print(f"   Step 4.1 Filtered CDB Rows: {len(cdb_filtered)}")

        # 2. 筛选 T7
        # 注意：先找到 CDB 中涉及的 Key
        valid_keys = cdb_filtered["Key"].unique()

        t7_filtered = t7[
            (t7["Year"] == year)
            & (t7["Scenario"] == scenario)
            & (t7["BL"] == target_bl)
            & (t7["Key"].isin(valid_keys))
        ].copy()
        print(f"   Step 4.2 Filtered T7 Rows: {len(t7_filtered)}")

        # 3. 聚合 Rate
        # 真实数据列名可能是 RateNo
        rate_col = "RateNo" if "RateNo" in t7_filtered.columns else "Value"
        t7_agg = t7_filtered.groupby(["Month", "Key"])[rate_col].sum().reset_index()
        t7_agg = t7_agg.rename(columns={rate_col: "Agg_Rate"})

        # 4. Merge
        merged = pd.merge(cdb_filtered, t7_agg, on=["Month", "Key"], how="left")

        # 5. Calculate
        merged["Agg_Rate"] = merged["Agg_Rate"].fillna(0)
        merged["Allocated_Amount"] = merged["Amount"] * merged["Agg_Rate"]

        # 6. Result
        result = merged.groupby("Month")["Allocated_Amount"].sum().reset_index()

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

        print("   ✅ Calculation Completed (First 5 rows):")
        print(result.head())

        self.state["execution_result"] = result
        return result

    def generate_sql(self):
        print("🔹 [Step 4] Generating SQL (Skipped for this test)...")
        return None

    def refine_answer(self):
        print("🔹 [Step 5] Refining Answer...")
        result = self.state.get("execution_result")
        intent = self.state.get("intent_analysis", {}).get("intent")

        if result is not None:
            if intent == "allocate_costs":
                total = result["Allocated_Amount"].sum()
                print(
                    f"   🤖 Final Answer: The allocated cost for {self.state['intent_analysis']['parameters']['target_bl']} is {total:,.2f}."
                )
            elif intent == "calculate_trend":
                print(
                    "   🤖 Final Answer: Trend analysis completed. See dataframe above."
                )
            elif intent == "analyze_cost_composition":
                print(
                    "   🤖 Final Answer: Composition analysis completed. See dataframe above."
                )
            elif intent == "compare_scenarios":
                print(
                    "   🤖 Final Answer: Scenario comparison completed. See dataframe above."
                )
            elif intent == "compare_allocated_costs":
                print(
                    "   🤖 Final Answer: Allocation comparison completed. See dataframe above."
                )
        else:
            print("   🤖 Final Answer: Failed to calculate.")


def run_test():
    print("🚀 Starting Allocation Logic Test Flow (Real Data)")
    print("=======================================")

    agent = MockAgentFlow()

    print("\n--- Test Case 1: Allocation ---")
    query1 = "请计算 2024年 Actual 场景下，CT 业务线分摊到的 IT Allocation 费用"
    agent.load_context(query1)
    agent.analyze_intent()
    agent.route()
    agent.refine_answer()

    print("\n--- Test Case 2: Trend Analysis ---")
    query2 = "请分析 2024年 Actual 场景下，HR Function 的成本月度趋势"
    agent.load_context(query2)
    agent.analyze_intent()
    agent.route()
    agent.refine_answer()

    print("\n--- Test Case 3: Cost Composition ---")
    query3 = "请分析 2024年 Actual 场景下，IT Function 的成本构成（按 Category）"
    agent.load_context(query3)
    agent.analyze_intent()
    agent.route()
    agent.refine_answer()

    print("\n--- Test Case 4: Scenario Comparison ---")
    query4 = "26财年采购的预算费用和25财年实际数比，变化是什么？"
    agent.load_context(query4)
    agent.analyze_intent()
    agent.route()
    agent.refine_answer()

    print("\n--- Test Case 5: Allocation Comparison ---")
    query5 = "26财年预算要分摊给413001的HR费用和25财年实际分摊给XP的HR费用相比，变化是怎么样的？"
    agent.load_context(query5)
    agent.analyze_intent()
    agent.route()
    agent.refine_answer()

    print("\n✅ All Tests Finished.")


if __name__ == "__main__":
    run_test()
