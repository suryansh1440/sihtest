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

def run_crewai_pipeline(query: str, verbose: bool = True) -> Dict[str, Any]:
    """Run the CrewAI pipeline for a user query and return a JSON-serializable dict.

    Parameters:
        query: Natural language request from the user.
        verbose: If True, prints progress messages.

    Returns:
        Dict matching FinalOutputModel schema.
    """

    # 1) First, run a tiny Router Crew to classify the query
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
    with MCPServerAdapter(server_params) as tools:
        if verbose:
            print(f"Available tools from Stdio MCP server: {[tool.name for tool in tools]}")

        # Only allow schema-related tools for the understand step
        schema_tools = [tool for tool in tools if getattr(tool, "name", "") in ["get_database_schema"]]


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
            tools=[*tools],
            verbose=True,
            llm=llm,
            max_iter=2
        )
        lookup_database_query = Task(
            description=(
                "Perform a SIMPLE LOOKUP based on the user's request using MCP DB tools for user query {query}. "
                "Prefer small aggregates such as COUNT(*), MIN/MAX, AVG by cycle if relevant. "
                "Return only a tiny result table with clear field names. Do not include graphs or maps."
                "first get the database schema then check the sql then excute query"
            ),
            agent=lookup_data_retrieval,
            expected_output="Small structured dataset with the requested lookup values.",
            tools=[*tools]
        )
        result_maker_lookup = Task(
            description=(
                    "Return ONLY FinalOutputModel with a short report summarizing fetched values. "
                    "Unless the user explicitly asked for graphs/maps, set graphs=[] and maps=[]."
            ),
            agent=lookup_data_retrieval,
            context=[lookup_database_query],
            output_json=FinalOutputModel,
            expected_output="JSON with report filled, graphs and maps likely empty"
        )




        # Report-only agents and tasks (heavy analysis)
        query_analyst = Agent(
            role="Query Analysis Specialist",
            goal="Understand user intent,get database schema and decompose complex queries into manageable sub-tasks and produce a concise plan of what geolocation info is needed to make report and generate map and graphs",
            backstory="You analyze the user's request and output exactly what geolocation (lat/lng of ocean regions like Atlantic or Indian Ocean) is needed and what the final JSON should contain.You are an expert at understanding natural language queries and breaking them down into clear, actionable components. You excel at identifying what information is needed and categorizing the type of request (data analysis, visualization, reporting).",
            tools=[*tools],
            verbose=True,
            llm=llm,
            max_iter=2
        )


        data_retrieval = Agent(
            role="Database Query Specialist", 
            goal="Execute database queries and retrieve relevant data using MCP tools and get only geolocation data using external search",
            backstory="You are a database expert who specializes in writing efficient SQL queries and retrieving data from databases. You use MCP tools to interact with Supabase and external search tools for supplementary data. When using SerperDevTool, ALWAYS use very specific search queries like'buoy indian ocean latitude longitude'. Never use broad searches. Limit to 1 targeted searches maximum.",
            tools=[SerperDevTool(), *tools],
            verbose=True,
            llm=llm,
            max_iter=4
        )

        data_analyst = Agent(
            role="Data Analysis & graph and map generation Specialist",
            goal="Analyze retrieved data & generate the final JSON report and map arrays in the exact specified format",
            backstory="""You are a data scientist who excels at analyzing datasets, 
            identifying patterns, and creating comprehensive reports. 
            You transform raw data into actionable insights and generate structured 
            outputs for visualization. 
            You perform statistical analysis manually and create detailed reports """,
            tools=[],
            verbose=True,
            llm=llm,
            max_iter=2
        )

        understand_request = Task(
            description="""Analyze the user query '{query}' and determine:
            1. Query type: station-specific, ocean-region, time-based, or comparison
            2. Target variables needed (temp, psal, etc.)
            3. Aggregation level required (by cycle, by station, by month, by ocean region)
            4. Geographic constraints (latitude/longitude ranges for ocean regions)
            5. Time constraints (specific months, years, or date ranges)
            
            For ocean regions, use these approximate boundaries:
            - Indian Ocean: 20°E to 120°E, 30°S to 30°N
            - Atlantic Ocean: 70°W to 20°E, 60°S to 65°N  
            - Pacific Ocean: 120°E to 70°W, 60°S to 65°N
            - Southern Ocean: South of 60°S
            - Arctic Ocean: North of 65°N
            
            Output a detailed plan specifying the exact aggregation strategy.""",
            agent=query_analyst,
            tools=schema_tools,
            expected_output="Detailed analysis of query type, required variables, aggregation level, and geographic/time constraints"
        )

        database_query = Task(
            description=(
                "Use MCP database tools to first inspect the schema, then EXECUTE AGGREGATED QUERIES based on user request: "
                "\n1. FOR STATION-SPECIFIC QUERIES: Extract platform_number and aggregate by cycle_number for that station"
                "\n2. FOR OCEAN-REGION QUERIES: Use latitude/longitude ranges to identify stations in that region, then aggregate by station or overall"
                "\n3. FOR TIME-BASED QUERIES: Extract month/year from date fields and aggregate accordingly"
                "\n4. ALWAYS use appropriate aggregation functions: AVG() for measurements, COUNT() for records"
                "\n\nExample SQL patterns:"
                "\n- Station-specific: SELECT cycle_number, AVG(temp) as temp, AVG(psal) as psal FROM measurements WHERE platform_number = '2902740' GROUP BY cycle_number"
                "\n- Ocean-region: SELECT platform_number, AVG(temp) as avg_temp, AVG(psal) as avg_psal FROM measurements WHERE latitude BETWEEN -10 AND 10 AND longitude BETWEEN 50 AND 100 GROUP BY platform_number"
                "\n- Monthly: SELECT EXTRACT(MONTH FROM date) as month, AVG(temp) as temp FROM measurements WHERE platform_number = '2902740' GROUP BY month"
                "\n\nReturn structured tabular results with clear field names matching the aggregation level."
            ),
            agent=data_retrieval,
            expected_output="Aggregated dataset appropriate for the query type with clear column names matching the requested variables",
            context=[understand_request],
            tools=[*tools]
        )

        external_geolocation_search = Task(
            description="Use SerperDevTool with VERY SPECIFIC queries to fetch precise latitude/longitude only if geolocation was requested. Limit to 1-2 searches. Return exact coordinates only.",
            agent=data_retrieval,
            expected_output="Exact lat/lng for requested regions or station if explicitly asked.",
            context=[understand_request],
            tools=[SerperDevTool()]
        )

        result_maker = Task(
            description=(
                "Generate the final JSON following FinalOutputModel strictly. Consider the aggregation level:"
                "\n- For station-specific queries: Create time series graphs with cycle_number on x-axis"
                "\n- For ocean-region queries: Create comparison graphs between stations or aggregate maps"
                "\n- For time-based queries: Use time units (months) on x-axis"
                "\n\nGraph creation rules:"
                "\n- Single variable: Line graph with xKey='cycle'/'month'/'station', yKey=[variable]"
                "\n- Multiple variables: Multiple lines or separate graphs"
                "\n- Comparison queries: Bar charts or grouped line charts"
                "\n- Always include all available data points, no truncation"
                "\n- Maps: Include only if geographic context was requested"
                "\n- Ensure all numeric values are properly formatted"
                "\n- For large result sets, focus on key trends rather than every data point"
            ),
            agent=data_analyst,
            context=[understand_request, database_query, external_geolocation_search],
            output_json=FinalOutputModel,
            expected_output="Well-structured JSON output with appropriate visualizations for the query type"
        )


        # crews for each route
        convo_crew = Crew(
            agents=[convo_agent],
            tasks=[convo_task],
            process="sequential",
            max_iter=1,
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
            max_iter=2,
            max_execution_time=120,
            verbose=True
        )
        report_crew = Crew(
            agents=[query_analyst, data_retrieval, data_analyst],
            tasks=[
                understand_request,
                database_query,
                external_geolocation_search,
                result_maker
            ],
            process="sequential",
            max_iter=2,
            max_execution_time=120,
            verbose=True
        )




        input_data = {"query": query}
        # run the crews from here 
        router_raw = router_crew.kickoff(input_data)
        router_raw = str(router_raw)
        cleaned_output = re.sub(r'```json\s*|\s*```', '', router_raw).strip()
        cleaned_output = cleaned_output.replace("'", '"')
        router_result = json.loads(cleaned_output)
        route = router_result['route']
        print(f"Router selected route: {route}")

        result = None
        if route == "CONVERSATION":
            result = convo_crew.kickoff(input_data)
        elif route == "LOOKUP":
            result = lookup_crew.kickoff(input_data)
        elif route == "REPORT":
            result = report_crew.kickoff(input_data)
        else:
            # Fallback to LOOKUP if unknown
            result = lookup_crew.kickoff(input_data)
        
        if isinstance(result, BaseModel):
            return result.model_dump()["json_dict"]
        elif isinstance(result, dict):
            return result["json_dict"]  
        else:
            text = str(result)
            cleaned = re.sub(r"```json\n?|\n?```", "", text).strip()
            cleaned_json =  json.loads(cleaned)
            return cleaned_json["json_dict"]
        

if __name__ == "__main__":
    demo_query = "hii how are you today"
    try:
        output = run_crewai_pipeline(demo_query, verbose=True)
        print("\nFINAL RESULT:\n", json.dumps(output, indent=2))
    except Exception as e:
        print("\nCREW EXECUTION FAILED:", str(e))