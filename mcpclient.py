from fastmcp import Client
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent,create_react_agent
from typing import Dict, Any, List
import asyncio
import json

# Configuration
GEMINI_API_KEY ="AIzaSyAScRxgclKcIb8ZUsQaLOsF2H6z7dqm2bg"
#  "AIzaSyBc8pyGVcgvpBFSp2v9hhDM8ZRtURYA8P8"
# "AIzaSyBDOujHS2CU3oCdFO9AQ5VLyBxRduOI5nU"
# "AIzaSyApuXIgRTrAIVBTouVjrjrd8iUwbtLz8lg"

# MCP configuration for HTTP transport
config = {
    "mcpServers": {
        "supabaseassistant": {"command": "python", "args": ["./supabaseserver.py"]}
        # "analysisagent": {"command": "python", "args": ["./analysisserver.py"]}
    }
}

# Do NOT create a long-lived client here; create per-call inside the function.

# Do not initialize the LLM at import time; create it per-call to avoid
# coupling to a closed asyncio event loop across requests.


async def mcp_answer_once(user_input: str) -> dict:
    """Execute a single MCP-powered answer and return a structured result.

    Parameters:
        user_input: The question or instruction to answer.

    Returns:
        A dictionary with keys: thought, content, graph, raw_output.
    """
    # Create a fresh client per call to avoid reusing a closed session
    client = Client(config)
    async with client:
        # Get the tools from the MCP client
        mcp_tools = await client.list_tools()

        # Convert MCP tools to LangChain tools
        langchain_tools = []

        def create_langchain_tool(mcp_tool_name, mcp_tool_description, server_name):
            """Create a LangChain tool wrapper for an MCP tool"""
            @tool
            async def tool_func(input: str = "") -> str:
                """Tool function for MCP tool"""
                # Handle different parameter patterns
                if input and input.strip():
                    # Convert input to proper parameter name based on tool
                    if mcp_tool_name in ("execute_sql", "check_sql"):
                        actual_kwargs = {"sql_query": input}
                    elif mcp_tool_name in ("analyze_data", "generate_html_report", "create_text_report"):
                        # For analysis tools, parse JSON input
                        try:
                            parsed_input = json.loads(input)
                            actual_kwargs = parsed_input
                        except json.JSONDecodeError:
                            # If not JSON, treat as simple string
                            actual_kwargs = {"data": {"rows": []}, "analysis_type": input}
                    else:
                        # For tools that don't need input, ignore the input
                        actual_kwargs = {}
                else:
                    # No input provided - for tools that don't need input
                    actual_kwargs = {}

                result = await client.call_tool(mcp_tool_name, actual_kwargs)
                return str(result)

            # Set the name and description manually with server prefix
            tool_func.name = f"{server_name}_{mcp_tool_name}"
            tool_func.description = f"[{server_name}] {mcp_tool_description}"
            return tool_func

        for mcp_tool in mcp_tools:
            # Determine server name based on tool name
            if mcp_tool.name in ["get_database_schema", "execute_sql", "check_sql"]:
                server_name = "supabase"
            elif mcp_tool.name in ["analyze_data", "generate_html_report", "create_text_report"]:
                server_name = "analysis"
            else:
                server_name = "supabase"  # default

            langchain_tool = create_langchain_tool(mcp_tool.name, mcp_tool.description, server_name)
            langchain_tools.append(langchain_tool)

        # Initialize the LLM per-request to avoid closed-loop issues
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0,
            google_api_key=GEMINI_API_KEY
        )

        # Use fully custom ReAct-style prompt with JSON output format
        prompt = ChatPromptTemplate.from_template(
            """You are a helpful assistant with strong data analysis skills. You can handle both general questions and database-related queries. Use tools ONLY for database schema or SQL data fetching.\n\nTools available:\n{tools}\n\nPOLICY\n- For general questions (greetings, general knowledge, non-database topics): Answer directly without using tools\n- For database queries: Use database tools for data retrieval (tables, schema, columns, relationships, data queries)\n- Perform all analysis in-model: aggregate, compare, find trends/anomalies, compute KPIs\n- Always consider if data visualization would be helpful and provide Plotly React code when applicable\n- IMPORTANT: Always consider 2 plausible approaches before acting. If the first fails or returns no rows, infer the user intent and try a different operator/approach once\n- CRITICAL: When you get database schema, you MUST proceed to execute the actual SQL query to answer the user's question\n\nWORKFLOW\n1) For general questions: Answer directly with JSON format\n2) For data queries: get_database_schema → check_sql → execute_sql (MUST complete all steps)\n3) For analysis requests: execute_sql (to fetch data) → reason in-model → summarize insights → emit Plotly code if applicable\n4) Quote reserved table names (e.g., user) with double quotes like \"user\"\n5) Do not repeat the same tool when the result is unchanged\n\nREACT FORMAT\nQuestion: the input question you must answer\nThought: outline 1-2 approaches before acting\n\nCRITICAL FORMATTING RULES:\n- If you can answer WITHOUT tools (general questions), IMMEDIATELY output:\n  Final Answer: {{\"thought\": [\"NA\"], \"content\": \"your answer\", \"graph\": \"NA\"}}\n- If you need database data, use this EXACT format:\n  Action: the action to take, one of [{tool_names}]\n  Action Input: the input to the action\n  Observation: the result of the action\n  ... (repeat Thought/Action/Action Input/Observation as needed)\n  Thought: I now know the final answer\n  Final Answer: {{\"thought\": [\"approach1\", \"approach2\"], \"content\": \"analysis results\", \"graph\": \"Plotly code or NA\"}}\n\nIMPORTANT: Do NOT output JSON in the middle of your reasoning. Only output JSON in the Final Answer.\n\nFINAL ANSWER FORMAT\nYour Final Answer MUST be a valid JSON object with this exact structure:\n\n{{\n  \"thought\": [\"approach1\", \"approach\"],\n  \"content\": \"your main response content here\",\n  \"graph\": \"Plotly React component code or 'NA' if no graph needed\"\n}}\n\nRULES FOR JSON OUTPUT:\n- For general questions: thought=[\"NA\"], content=your answer, graph=\"NA\"\n- For database queries: thought=[\"approach1\", \"approach2\"], content=analysis results, graph=Plotly code or \"NA\"\n- For data visualization: graph should contain complete React component with Plotly.js\n- Always ensure valid JSON format with proper escaping\n\nBegin!\n\nQuestion: {input}\nThought:{agent_scratchpad}"""
        )

        # Create the agent with the built-in ReAct prompt
        agent = create_react_agent(llm, langchain_tools, prompt)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=langchain_tools,
            verbose=True,
            handle_parsing_errors=True,
            return_intermediate_steps=True,
            max_iterations=5,
        )

        # Process the user's input once
        response = await agent_executor.ainvoke({"input": user_input})

        output = response.get('output', '') if isinstance(response, dict) else str(response)

        # Try to parse JSON output
        try:
            json_start = output.find('{')
            json_end = output.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = output[json_start:json_end]
                parsed_json = json.loads(json_str)
                return {
                    "thought": parsed_json.get("thought", "N/A"),
                    "content": parsed_json.get("content", "N/A"),
                    "graph": parsed_json.get("graph", "N/A"),
                    "raw_output": output,
                }
        except json.JSONDecodeError:
            pass

        # Fallback shape if no JSON could be parsed
        return {
            "thought": "N/A",
            "content": output or "Sorry, I couldn't process that request.",
            "graph": "NA",
            "raw_output": output,
        }


def mcp_answer(user_input: str) -> dict:
    """Synchronous wrapper around mcp_answer_once for easy importing.

    Example:
        from mcpclient import mcp_answer
        result = mcp_answer("list all tables")
    """
    return asyncio.run(mcp_answer_once(user_input))

if __name__ == "__main__":
    # One-shot CLI usage (no loop)
    try:
        user_input = input("\nYou (one-shot): ").strip()
        result = asyncio.run(mcp_answer_once(user_input))
        print("\nAssistant Response:")
        print(f"Thought: {result.get('thought')}")
        print(f"Content: {result.get('content')}")
        graph = result.get('graph')
        if graph and graph != 'NA':
            print("\nGraph (Plotly React Code):")
            print(f"```jsx\n{graph}\n```")
        else:
            print(f"Graph: {graph}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")