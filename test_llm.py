import os

os.environ["NO_PROXY"] = "localhost,127.0.0.1"

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

llm = ChatOpenAI(
    model="qwen2.5:1.5b",
    api_key="ollama",
    base_url="http://127.0.0.1:11434/v1",
    temperature=0.1,
)

try:
    print("Invoking LLM...")
    response = llm.invoke([HumanMessage(content="hello")])
    print("Response:", response.content)
except Exception as e:
    print("Error:", e)
