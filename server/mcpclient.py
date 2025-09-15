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
GEMINI_API_KEY = "AIzaSyAScRxgclKcIb8ZUsQaLOsF2H6z7dqm2bg"
# "AIzaSyBc8pyGVcgvpBFSp2v9hhDM8ZRtURYA8P8"
# "AIzaSyBDOujHS2CU3oCdFO9AQ5VLyBxRduOI5nU"
# "AIzaSyApuXIgRTrAIVBTouVjrjrd8iUwbtLz8lg"

# MCP configuration for HTTP transport
config = {
    "mcpServers": {
        "supabaseassistant": {"command": "python", "args": ["./supabaseserver.py"]},
        "mapdataserver": {"command": "python", "args": ["./mapdataserver.py"]}
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
            elif mcp_tool.name in ["generate_map_data", "get_coordinate_info", "analyze_map_request"]:
                server_name = "mapdata"
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
            """You are a helpful assistant with strong data analysis skills and map visualization capabilities. You can handle general questions, database-related queries, and map data generation.
            
            Tools available:
            {tools}
            
            POLICY
            - For general questions (greetings, general knowledge, non-database topics): Answer directly without using tools
            - For database queries: Use database tools for data retrieval (tables, schema, columns, relationships, data queries)
            - For map visualization requests: Use map data tools to generate labels, hex bin, or heatmap data
            - Perform all analysis in-model: aggregate, compare, find trends/anomalies, compute KPIs
            - IMPORTANT: Always consider 2 plausible approaches before acting. If the first fails or returns no rows, infer the user intent and try a different operator/approach once
            - CRITICAL: When you get database schema, you MUST proceed to execute the actual SQL query to answer the user's question
            - MAP DATA: For map requests, analyze the user's intent and generate appropriate visualization data
            
            WORKFLOW
            1) For general questions: Answer directly with JSON format
            2) For data queries: get_database_schema → check_sql → execute_sql (MUST complete all steps)
            3) For analysis requests: execute_sql (to fetch data) → reason in-model → summarize insights → emit graph SPECS (not code)
            4) For map visualization: analyze_map_request → generate_map_data → return structured map data
            5) Quote reserved table names (e.g., user) with double quotes like \"user\"
            6) Do not repeat the same tool when the result is unchanged
            
            MAP DATA TOOL USAGE:
            - For generate_map_data: Use format \"analysis_type,region,data_source\" (e.g., \"heatmap,indian_ocean,knowledge\")
            - For get_coordinate_info: Use location name (e.g., \"Mumbai\")
            - For analyze_map_request: Use natural language query (e.g., \"Show me cities in India with heatmap\")
            
             REACT FORMAT
             Question: the input question you must answer
             Thought: outline 1-2 approaches before acting
             Action: the action to take, one of [{tool_names}]
             Action Input: the input to the action
             Observation: the result of the action
             ... (repeat Thought/Action/Action Input/Observation as needed)
             Thought: I now know the final answer
             Final Answer: {{"thought": ["approach1", "approach2"], "content": "analysis results", "graphs": [GRAPH_SPEC, GRAPH_SPEC, GRAPH_SPEC], "map_data": MAP_DATA_SPEC}}
             
             CRITICAL FORMATTING RULES:
             - If you can answer WITHOUT tools (general questions), IMMEDIATELY output:
               Final Answer: {{"thought": ["NA"], "content": "your answer", "graphs": [], "map_data": null}}
             - If you need database data, ALWAYS follow the ReAct format above
             - NEVER skip the Action: and Action Input: lines when using tools
            
            IMPORTANT: Do NOT output JSON in the middle of your reasoning. Only output JSON in the Final Answer.
            
            FINAL ANSWER FORMAT
            Your Final Answer MUST be a valid JSON object with this exact structure:
            
            {{
            \"thought\": [\"approach1\", \"approach2\"],
            \"content\": \"your main response content here\",
            \"graphs\": [GRAPH_SPEC, GRAPH_SPEC, GRAPH_SPEC],
            \"map_data\": MAP_DATA_SPEC (only for map visualization requests)
            }}
            
            
            GRAPH_SPEC SCHEMA (STRICT):
            Each GRAPH_SPEC MUST be a JSON object with these fields (no code strings).
            
            \"type\": one of [\"bar\", \"line\", \"pie\", \"scatter\", \"area\"],
            \"title\": string,
            \"description\": string,
            \"data\": [ ...key:value pairs per point... ],
            \"xKey\": string,              // key for x-axis/category/time
            \"yKey\": string OR [string],  // key(s) for y values/series (array for multi-series)
            \"seriesNames\": [string],     // optional names for multi-series
            \"colors\": [string]           // optional hex/color names
            
            MAP_DATA_SPEC SCHEMA (for map visualization requests):
            MAP_DATA_SPEC MUST be a JSON object with these fields:
            
            \"title\": string,             // Map visualization title
            \"description\": string,        // Map visualization description
            \"visualization_type\": string, // \"labels\", \"hexbin\", \"heatmap\", or \"all\"
            \"region\": string,            // Geographic region
            \"data\": {{
                \"labels\": [              // Optional labels layer data
                    {{\"lat\": number, \"lng\": number, \"text\": string, \"color\": string, \"size\": number, \"altitude\": number}}
                ],
                \"hexbin\": [              // Optional hex bin layer data
                    {{\"lat\": number, \"lng\": number, \"weight\": number}}
                ],
                \"heatmap\": [             // Optional heatmap layer data
                    {{\"lat\": number, \"lng\": number, \"weight\": number}}
                ]
            }}
            
            
            DATA REQUIREMENTS:
            - Populate each GRAPH_SPEC.data with REAL, non-empty arrays derived from fetched results
            - Use compact field names without spaces: snake_case or camelCase (e.g., cycle, avg_pressure)
            - Total points across all graphs must be ≤ 200
            - If data is unavailable, return graphs: []
            
             SQL AGGREGATION POLICY (CRITICAL):
             - ALWAYS use SQL aggregation (AVG, COUNT, SUM, MAX, MIN) when data volume is high
             - If you suspect > 500 rows, write SQL with GROUP BY, AVG(), COUNT() instead of SELECT *
             - For time series: use DATE_TRUNC() to bucket by day/month/year
             - For distributions: create bins in SQL with CASE statements, then COUNT() each bin
             - For averages: use AVG(column) GROUP BY category instead of fetching all raw values
             - NEVER fetch entire large tables; always aggregate first in SQL
             - Keep total points across all graphs ≤ 200
            
            GRAPHING RULES:
            - Generate 1-3 graphs maximum in the \"graphs\" array
            - Choose chart types based on data suitability
            - Do NOT use type \"histogram\"; for distributions use type \"bar\" with binned counts
            - Keep data concise and well-labeled
            - If no visualization is needed, use empty array: \"graphs\": []
            - For general questions: \"graphs\": []
            
            RULES FOR JSON OUTPUT:
            - For general questions: thought=[\"NA\"], content=your answer, graphs=[], map_data=null
            - For database queries: thought=[\"approach1\", \"approach2\"], content=analysis results, graphs=[GRAPH_SPEC...], map_data=null
            - For map visualization: thought=[\"approach1\", \"approach2\"], content=map analysis, graphs=[], map_data=MAP_DATA_SPEC
            - Always ensure valid JSON format with proper escaping
            
            Begin!
            
            Question: {input}
            Thought:{agent_scratchpad}"""
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
        
        # Clean the text to extract JSON from markdown code blocks
        import re
        cleanText = re.sub(r'```json\n?|\n?```', '', output).strip()
        
        try:
            # Parse the cleaned text as JSON
            topics = json.loads(cleanText)
            return topics
        except json.JSONDecodeError:
            # If JSON parsing fails, return the raw output in a structured format
            return {
                "thought": ["JSON parsing failed"],
                "content": output,
                "graphs": []
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
        graphs = result.get('graphs', [])
        if graphs:
            print(f"\nGraphs ({len(graphs)} total):")
            for i, graph in enumerate(graphs, 1):
                print(f"\n--- Graph {i} (Plotly React Code) ---")
                print(f"```jsx\n{graph}\n```")
        else:
            print("Graphs: None")
    except Exception as e:
        print(f"An error occurred: {str(e)}")