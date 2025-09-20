from dotenv import load_dotenv
load_dotenv()
import os
import json
import re
import logging
from datetime import datetime

from crewai import LLM,Agent,Task,Crew
from crewai_tools import SerperDevTool
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union, Literal

# Import socket manager for real-time updates
try:
    from socket_manager import socket_manager
    SOCKET_AVAILABLE = True
except ImportError:
    SOCKET_AVAILABLE = False
    socket_manager = None


# Configure LLM for Gemini
llm = LLM(
    model="gemini/gemini-2.0-flash",
    temperature=0.1,
    api_key=os.getenv("GEMINI_API_KEY")  # Use the correct environment variable
)

class MapLabel(BaseModel):
    lat: float
    lng: float
    text: str
    color: str
    size: float
    altitude: float

class MapHexbin(BaseModel):
    lat: float
    lng: float
    weight: float

class MapHeatmap(BaseModel):
    lat: float
    lng: float
    weight: float

# Define the models for each map type using discriminated unions
class BaseMap(BaseModel):
    title: str
    description: str

class LabelsMap(BaseMap):
    type: Literal["labels"] = "labels"
    data: List[MapLabel] = Field(..., description="List of label data points.")

class HexbinMap(BaseMap):
    type: Literal["hexbin"] = "hexbin"
    data: List[MapHexbin] = Field(..., description="List of hexbin data points.")

class HeatmapMap(BaseMap):
    type: Literal["heatmap"] = "heatmap"
    data: List[MapHeatmap] = Field(..., description="List of heatmap data points.")

# Union to allow the 'maps' list to contain different types of map objects
MapItem = Union[LabelsMap, HexbinMap, HeatmapMap]

# Pydantic model for report content
class Report(BaseModel):
    title: str
    content: str

# Pydantic model for graph data
class Graph(BaseModel):
    type: str = Field(..., description="The type of chart, e.g., 'bar', 'line', 'pie', etc.")
    title: str = Field(..., description="Title of the graph.")
    description: str = Field(..., description="A brief description of what the graph shows.")
    data: List[Dict[str, Any]] = Field(..., description="The data points for the chart. Each item is a dictionary.")
    xKey: str = Field(..., description="The key in the data dictionaries to use for the x-axis.")
    yKey: Union[str, List[str]] = Field(..., description="The key(s) in the data dictionaries to use for the y-values.")
    seriesNames: Optional[List[str]] = None
    colors: Optional[List[str]] = None

# The final Pydantic model for the complete result
class FinalOutputModel(BaseModel):
    thought: str = Field(..., description="The agent's internal thought process and reasoning.")
    report: Report
    graphs: List[Graph]
    maps: List[MapItem]

class RouterOutput(BaseModel):
    route: Literal["CONVERSATION", "LOOKUP", "REPORT"]


# Removed JSON report generator tool per requirements

server_params = StdioServerParameters(
    command=".venv/Scripts/python.exe", 
    args=["mcpServers/supabaseserver.py"],
    env={"UV_PYTHON": "3.12", **os.environ},
    
)

def emit_progress(session_id: str, stage: str, message: str):
    """Emit progress update if socket manager is available"""
    if SOCKET_AVAILABLE and socket_manager and session_id:
        socket_manager.emit_progress(session_id, stage, message)

def run_crewai_pipeline(query: str, verbose: bool = True, session_id: str = None) -> Dict[str, Any]:
    """Run the CrewAI pipeline for a user query and return a JSON-serializable dict.

    Parameters:
        query: Natural language request from the user.
        verbose: If True, prints progress messages.

    Returns:
        Dict matching FinalOutputModel schema.
    """

    # Emit initial progress
    emit_progress(session_id, 'initialization', 'Setting up CrewAI pipeline...')
    
    # 1) First, run a tiny Router Crew to classify the query
    emit_progress(session_id, 'routing', 'Creating router agent...')
    router_agent = Agent(
        role="Router",
        goal="Classify the user's query.",
        backstory=(
            "Your ONLY job is to classify the query. Output exactly one word: "
            "CONVERSATION, LOOKUP, or REPORT."
        ),
        verbose=True,
        llm=llm,
        max_iter=1
    )
    route_task = Task(
        description=(
            "Classify this query: '{query}'.\n"
            "Rules:\n"
            "- CONVERSATION: greetings/small talk/general chat.\n"
            "- LOOKUP: simple data lookup (brief values), no graphs/maps unless requested.\n"
            "- REPORT: full analysis/report with possible graphs/maps if relevant.\n"
            "Output JSON exactly as: {\"route\": \"CONVERSATION\"} or {\"route\": \"LOOKUP\"} or {\"route\": \"REPORT\"}. No other text.\n"
            "Examples:\n"
            "- 'hi how are you' => {\"route\": \"CONVERSATION\"}\n"
            "- 'give me count of all cycles for 19005' => {\"route\": \"LOOKUP\"}\n"
            "- 'analyze trends and create graphs in alantic ocean' => {\"route\": \"REPORT\"}"
        ),
        agent=router_agent,
        output_json=RouterOutput,
        expected_output="JSON with a single 'route' field"
    )
    router_crew = Crew(
        agents=[router_agent],
        tasks=[route_task],
        process="sequential",
        max_iter=1,
        max_execution_time=30,
        verbose=True
    )
    # 2) Run the appropriate specialized crew
    emit_progress(session_id, 'tools', 'Connecting to database tools...')
    with MCPServerAdapter(server_params) as tools:
        if verbose:
            print(f"Available tools from Stdio MCP server: {[tool.name for tool in tools]}")
        
        emit_progress(session_id, 'tools', f'Connected to {len(tools)} database tools')


        # convo agent and task
        convo_agent = Agent(
            role="Conversational Assistant",
            goal="Respond to greetings or general chat tersely user query {query}.",
            backstory="You keep responses short and helpful. No tools.",
            verbose=False,
            llm=llm,
            max_iter=1
        )
        convo_task = Task(
            description=(
                    "Produce FinalOutputModel: a brief friendly reply in report.content for user query {query}. "
                    "Set graphs=[] and maps=[]. Keep report.title='Assistant'."
            ),
            agent=convo_agent,
            output_json=FinalOutputModel,
            expected_output="A single JSON object with minimal reply"
        )





        # Lookup-only agent (no heavy analysis)
        lookup_data_retrieval = Agent(
            role="Database query Specialist",
            goal="Perform simple database lookups and brief aggregations; return concise values only.",
            backstory="You fetch small, targeted results fast. No graphs or maps unless explicitly asked.",
            verbose=True,
            llm=llm,
            max_iter=2
        )
        lookup_database_query = Task(
            description=(
                "Perform a SIMPLE LOOKUP based on the user's request using MCP DB tools for user query {query}. "
                "Prefer small aggregates such as COUNT(*), MIN/MAX, AVG by cycle if relevant. "
                "Return only a tiny result table with clear field names. Do not include graphs or maps."
                "first get the database schema then excute query"
            ),
            agent=lookup_data_retrieval,
            expected_output="Small structured dataset with the requested lookup values.",
            tools=[*tools]
        )
        result_maker_lookup = Task(
            description=(
                    "Return ONLY FinalOutputModel with a 2-3 sentences report summarizing fetched values. "
                    "Unless the user explicitly asked for graphs/maps, set graphs=[] and maps=[]."
            ),
            agent=lookup_data_retrieval,
            context=[lookup_database_query],
            output_json=FinalOutputModel,
            expected_output="JSON with report filled with 2-3 sentences, graphs and maps likely empty"
        )




        # Report-only agents and tasks (heavy analysis)
        data_analyst = Agent(
            role="Data Analysis & Report Generation Specialist",
            goal=(
                "Understand the user's query, determine needed variables, station/region and time scope; "
                "fetch required datasets via available tools (including geolocations from DB); "
                "prepare clean aggregated data and then produce a high-quality report, graphs and maps."
            ),
            backstory="""You are a data scientist who can interpret the user's intent, decide what to query,
            use available tools to fetch exactly what's needed, aggregate by cycle/station/month as appropriate,
            and then create compelling reports with meaningful graphs and map layers in the required schema.""",
            tools=[*tools],
            verbose=True,
            llm=llm,
            max_iter=3
        )

        result_agent = Agent(
            role="Data Visualization and Report Creator",
            goal="""From the provided structured data, create the best possible report with high-quality graphs and maps,
                    adhering strictly to the FinalOutputModel schema.""",
            backstory="""You are a master at converting raw data into clear, insightful, and visually appealing reports.
                        You understand which chart and map types best represent the data to tell a compelling story.""",
            verbose=True,
            llm=llm,
            max_iter=1
        )


        # Single task where data_analyst interprets the query and fetches data
        analysis_and_fetch = Task(
            description=(
                "For the query: '{query}', perform ALL of the following:\n"
                "first get the count of row you want to fetch from the database"
                "then if data is more than 200 rows then fetch only 200 rows by using the avg and get average the data if its is meaniningfull."
                "if ask about cycles then fetch data according to the cycle of a specific platform number dont use the avg in this"
                "if ask about platform number then fetch data according to the avg cycles data of that station"
                "if ask about region then get the region lat,log then fetch meserments data according to it in avg."
                "if ask about date then fetch according to the avg stations data"
                "1) Interpret intent: extract station/platform number/cycles etc, if present; identify requested variables (e.g., temp, psal); time scope; and whether maps are needed.\n"
                "2) Use DB tools to retrieve required data. Prefer aggregated data averages for queries. Include lat/lng for map labels when relevant.\n"
                "3) Produce a concise, structured summary of fetched results suitable for rendering graphs and maps (no markdown)."
            ),
            agent=data_analyst,
            tools=[*tools],
            expected_output="Structured findings and tabular aggregates ready to render"
        )



        result_maker = Task(
            description=(
                "Generate ONLY the final JSON strictly matching FinalOutputModel. Use the context data to build:\n"
                "- report.title and report.content (clear, non-generic and insightful).\n"
                "- graphs: create a maximum of 2 graphs relevant to the data. Choose from types like 'bar', 'line', 'scatter', 'area', or 'pie'.\n"
                "  **CRITICAL: Each graph's 'data' array must contain actual data points, not empty objects. Each data point should be a dictionary with the xKey and yKey values.**\n"
                "  For example: [{\"cycle\": 1, \"temp\": 23.1}, {\"cycle\": 2, \"temp\": 24.5}] for a line graph with xKey='cycle' and yKey='temp'.\n"
                "  For example: [{\"station\": \"A\", \"pressure\": 1013}, {\"station\": \"B\", \"pressure\": 1015}] for a bar chart with xKey='station' and yKey='pressure'.\n"
                "- maps: create a maximum of 1 map. If the data includes temperature, use a 'heatmap'. For general location data, use a 'labels' map.\n"
                "  **For a 'hexbin' map, think of it as bars coming upward from the map, where the height of the bar represents a value like density or count.**\n"
                "  The map type should be chosen to best represent the spatial data (e.g., 'heatmap' for density, 'labels' for specific points).\n"
                "  **CRITICAL: Each map's 'data' array must contain actual coordinate and weight data, not empty objects.**\n"
                "No extra keys; numbers must be numeric. Ensure all keys (`xKey`, `yKey`, `lat`, `lng`, etc.) are correctly mapped from the data.\n"
                "**MOST IMPORTANT: Fill the 'data' arrays with actual values from the context, not empty objects {}.**"
            ),
            agent=result_agent,
            context=[analysis_and_fetch],
            output_json=FinalOutputModel,
            expected_output="A single JSON object formatted as per FinalOutputModel with a high-quality narrative, graphs, and maps"
        )

        # crews for each route
        convo_crew = Crew(
            agents=[convo_agent],
            tasks=[convo_task],
            process="sequential",
            max_iter=5,
            max_execution_time=30,
            verbose=True
            )
        lookup_crew = Crew(
            agents=[lookup_data_retrieval],
            tasks=[
                lookup_database_query,
                result_maker_lookup
            ],
            process="sequential",
            max_iter=5,
            max_execution_time=120,
            verbose=True
        )
        report_crew = Crew(
            agents=[data_analyst,result_agent],
            tasks=[
                analysis_and_fetch,
                result_maker
            ],
            process="sequential",
            max_iter=5,
            max_execution_time=120,
            verbose=True
        )




        input_data = {"query": query}
        # run the crews from here 
        emit_progress(session_id, 'routing', 'Classifying query type...')
        router_raw = router_crew.kickoff(input_data)
        router_raw = str(router_raw)
        cleaned_output = re.sub(r'```json\s*|\s*```', '', router_raw).strip()
        cleaned_output = cleaned_output.replace("'", '"')
        router_result = json.loads(cleaned_output)
        route = router_result['route']
        print(f"Router selected route: {route}")
        emit_progress(session_id, 'routing', f'Query classified as: {route}')

        result = None
        if route == "CONVERSATION":
            emit_progress(session_id, 'processing', 'Running conversation crew...')
            result = convo_crew.kickoff(input_data)
        elif route == "LOOKUP":
            emit_progress(session_id, 'processing', 'Running lookup crew...')
            result = lookup_crew.kickoff(input_data)
        elif route == "REPORT":
            emit_progress(session_id, 'processing', 'Running report crew...')
            emit_progress(session_id, 'analysis', 'Performing data analysis...')
            result = report_crew.kickoff(input_data)
        else:
            # Fallback to LOOKUP if unknown
            emit_progress(session_id, 'processing', 'Running fallback lookup crew...')
            result = lookup_crew.kickoff(input_data)
            result = str(result)
        
        emit_progress(session_id, 'finalization', 'Processing results...')
        
        # Parse the raw output from CrewAI
        if hasattr(result, 'raw') and result.raw:
            # Try to parse the raw JSON output
            try:
                cleaned = re.sub(r"```json\n?|\n?```", "", str(result.raw)).strip()
                cleaned = cleaned.replace("'", '"')
                return json.loads(cleaned)
            except:
                # Fallback to string representation
                return {"result": str(result.raw)}
        else:
            # Fallback if no raw output
            return {"result": str(result)}

        

if __name__ == "__main__":
    demo_query = "hii how are you today"
    try:
        output = run_crewai_pipeline(demo_query, verbose=True)
        print("\nFINAL RESULT:\n", json.dumps(output, indent=2))
    except Exception as e:
        print("\nCREW EXECUTION FAILED:", str(e))