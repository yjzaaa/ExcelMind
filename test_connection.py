import sys
import os
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from excel_agent.config import get_config
from excel_agent.stream import get_llm


def test_connection():
    # 1. Load env vars
    print("1. Loading environment variables...")
    load_dotenv()

    # 2. Load config
    print("2. Loading configuration...")
    config = get_config()

    # 3. Check active provider
    active_provider = config.model.active
    print(f"   Active provider: {active_provider}")

    provider_config = config.model.get_active_provider()
    print(f"   Provider config: {provider_config.description}")
    print(f"   API Key configured: {'Yes' if provider_config.api_key else 'No'}")

    if not provider_config.api_key:
        print("❌ Error: API Key is missing!")
        return

    # 4. Initialize LLM
    print("3. Initializing LLM...")
    try:
        llm = get_llm()
        print("   LLM initialized successfully.")
        # print(f"   Base URL: {llm.base_url}") # ChatOpenAI object might not have base_url attribute directly accessible this way depending on version

        # 5. Test Invocation
        print("4. Testing API invocation (Sending 'Hello')...")
        from langchain_core.messages import HumanMessage

        response = llm.invoke([HumanMessage(content="Hello, are you ready?")])
        print(f"   Response: {response.content}")

    except Exception as e:
        print(f"❌ Error: {e}")
        return

    print("\n✅ Connection test passed (invocation level).")


if __name__ == "__main__":
    test_connection()
