from langchain.chat_models import init_chat_model
from langchain_openai import ChatOpenAI

from excel_agent.config import get_config

import os


def get_llm():
    """获取 LLM 实例"""
    config = get_config()
    provider = config.model.get_active_provider()
    return init_chat_model(
        model=os.getenv("OPENAI_MODEL_ID"),
        model_provider=os.getenv("OPENAI_MODEL_PROVIDER"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        api_version=os.getenv("OPENAI_API_VERSION"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.5,
    )

    return ChatOpenAI(
        model=provider.model_name,
        api_key=provider.api_key,
        base_url=provider.base_url if provider.base_url else None,
        temperature=provider.temperature,
        max_tokens=provider.max_tokens,
    )
