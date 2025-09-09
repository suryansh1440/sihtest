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
# from langchain_ollama import ChatOllama

# Configuration
GEMINI_API_KEY = "AIzaSyBDOujHS2CU3oCdFO9AQ5VLyBxRduOI5nU"
# "AIzaSyBc8pyGVcgvpBFSp2v9hhDM8ZRtURYA8P8"
# "AIzaSyApuXIgRTrAIVBTouVjrjrd8iUwbtLz8lg"
# "AIzaSyAScRxgclKcIb8ZUsQaLOsF2H6z7dqm2bg"

# MCP configuration for HTTP transport
config = {
    "mcpServers": {
        # "sqlassistant": {"command": "python", "args": ["./sqlserver.py"]},
        "supabaseassistant": {"command": "python", "args": ["./supabaseserver.py"]}
    }
}

# Create a client that connects to all servers
client = Client(config)

# Initialize the LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0,
    convert_system_message_to_human=True,
    google_api_key=GEMINI_API_KEY
)

# llm = ChatOllama(model="gemma3:1b", temperature=0)


async def main():
    async with client:
        try:
            # Get the tools from the MCP client
            mcp_tools = await client.list_tools()
            print(f"Available MCP tools: {[tool.name for tool in mcp_tools]}")
            
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
                        if mcp_tool_name == "execute_sql":
                            actual_kwargs = {"sql_query": input}
                        elif mcp_tool_name == "describe_table":
                            actual_kwargs = {"table_name": input}
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
                # Since we're only using one server, use the tool name directly
                langchain_tool = create_langchain_tool(mcp_tool.name, mcp_tool.description, "supabase")
                langchain_tools.append(langchain_tool)
            
            # Use fully custom ReAct-style prompt (no built-in prompt) with DB-safe workflow
            prompt = ChatPromptTemplate.from_template(
                """You are a helpful assistant. Use your own knowledge first. Use tools when needed.\n\nTools available:\n{tools}\n\nPOLICY\n- Prefer your own knowledge for general questions.\n- Use database tools only for DB-specific requests (tables, schema, columns, relationships, data retrieval).\n- IMPORTANT: Consider 2 plausible approaches before acting. If the first fails or no row return think want user would want, try the second once and before using that you are not same as before and try different approch or different operator if possible.\n- On tool errors, reinterpret the intent and adjust once; do not loop failing calls.\n\nDATABASE WORKFLOW (STRICT)\n1) For any data retrieval, first call get_table_names once to confirm table names.\n2) Quote reserved table names like \"user\" with double quotes.\n3) Run a single SELECT via execute_sql (specific fields if requested, otherwise *).\n4) Only call describe_table if needed to decide columns.\n5) Do not repeat the same tool when the result is unchanged.\n\nFORMAT\nQuestion: the input question you must answer\nThought: outline 1-2 approaches before acting\nAction: the action to take, one of [{tool_names}]\nAction Input: the input to the action\nObservation: the result of the action\n... (repeat Thought/Action/Action Input/Observation as needed)\nThought: I now know the final answer\nFinal Answer: the final answer to the original input question\n\nBegin!\n\nQuestion: {input}\nThought:{agent_scratchpad}"""
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
                early_stopping_method="generate"
            )
            
            # Example interaction loop
            while True:
                user_input = input("\nYou: ").strip()
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("Goodbye!")
                    break
                    
                try:
                    # Process the user's input
                    response = await agent_executor.ainvoke({"input": user_input})
                    
                    # Extract and display the final answer
                    if 'output' in response:
                        print(f"\nAssistant: {response['output']}")
                    else:
                        print("\nSorry, I couldn't process that request.")
                        
                except Exception as e:
                    print(f"\nAn error occurred: {str(e)}")
        
        except Exception as e:
            print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())