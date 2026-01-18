import pandas as pd
from excel_agent.excel_loader import get_loader
from excel_agent.logger import setup_logging, get_logger

setup_logging()
logger = get_logger("inspector")

def inspect():
    file_path = r"D:\AI_Python\AI2\AI2\back_end_code\Data\Function cost allocation analysis to IT 20260104.xlsx"
    loader = get_loader()
    loader.add_table(file_path, sheet_name="CostDataBase")
    
    loader = loader.get_active_loader()
    df = loader.dataframe
    
    logger.info(f"Columns: {df.columns.tolist()}")
    logger.info(f"Head:\n{df.head().to_markdown()}")

if __name__ == "__main__":
    inspect()
