I will implement a single-purpose agent for cost allocation in `src/excel_agent/allocationagent.py` using LangChain's `create_tool_calling_agent`.

### Implementation Plan

1.  **Setup Imports**:
    -   Import `ChatOpenAI`, `ChatPromptTemplate`, `AgentExecutor`, and `create_tool_calling_agent`.
    -   Import project utilities: `get_config`, `calculate_allocated_costs` (tool), and `get_logger`.

2.  **LLM Configuration**:
    -   Implement a `get_llm()` helper to instantiate `ChatOpenAI` using the project's configuration (model name, API key, base URL).

3.  **Define Agent Prompt**:
    -   Create a `ChatPromptTemplate` with:
        -   A system message instructing the agent to act as a specialized cost allocation assistant.
        -   A placeholder for `chat_history` (optional but good practice) and `user_input`.
        -   The mandatory `agent_scratchpad` placeholder for tool invocation history.

4.  **Create Agent Factory**:
    -   Implement `create_allocation_agent_executor()`:
        -   Initialize the LLM.
        -   Define the tool list: `[calculate_allocated_costs]`.
        -   Construct the agent using `create_tool_calling_agent`.
        -   Return an `AgentExecutor` wrapping the agent and tools.

5.  **Add Execution Helper**:
    -   Implement `run_allocation_agent(query: str)` to simplify invocation.

### Verification Plan
-   Create a test script `test_allocation_agent_simple.py` to run the agent with a sample query (e.g., "Calculate allocated costs for CT in FY25 Actual").
-   Verify that the agent calls the `calculate_allocated_costs` tool and returns a natural language response based on the tool's output.