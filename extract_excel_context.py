import pandas as pd
import os

file_path = r"D:\AI_Python\AI2\AI2\back_end_code\Data\Function cost allocation analysis to IT 20260104.xlsx"

try:
    xl = pd.ExcelFile(file_path)
    print(f"Sheet names: {xl.sheet_names}")
    
    md_content = "# Excel Data Analysis Context\n\n"
    
    # Process "解释和逻辑" sheet if it exists
    sheet_logic = "解释和逻辑"
    if sheet_logic in xl.sheet_names:
        df_logic = pd.read_excel(file_path, sheet_name=sheet_logic)
        md_content += f"## Sheet: {sheet_logic}\n\n"
        md_content += df_logic.to_markdown(index=False)
        md_content += "\n\n"
    else:
        print(f"Warning: Sheet '{sheet_logic}' not found.")

    # Process "问题" sheet if it exists
    sheet_questions = "问题"
    if sheet_questions in xl.sheet_names:
        df_questions = pd.read_excel(file_path, sheet_name=sheet_questions)
        md_content += f"## Sheet: {sheet_questions}\n\n"
        md_content += df_questions.to_markdown(index=False)
        md_content += "\n\n"
    else:
        print(f"Warning: Sheet '{sheet_questions}' not found.")
        
    output_path = "docs/excel_context.md"
    os.makedirs("docs", exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    print(f"Markdown file generated at: {output_path}")

except Exception as e:
    print(f"Error: {e}")
