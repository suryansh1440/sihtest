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
    with MCPServerAdapter(server_params) as tools:
        if verbose:
            print(f"Available tools from Stdio MCP server: {[tool.name for tool in tools]}")

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
            description="""Analyze the user query '{query}' and specify:
            - Target ocean region(s) requiring geolocation (e.g., Indian Ocean, Atlantic Ocean)
            - Exactly what lat/lng to retrieve (central or representative coordinates)
            - Get database schema to understand the data you need to retrieve from the database and from the external search.
            Output a concise plan.
            You must use the tools available to you to get the data you need.""",
            agent=query_analyst,
            tools=[*tools],
            expected_output="Plan listing ocean regions and the exact geolocation info to fetch and from where to fetch the data"
        )

        database_query = Task(
            description=(
                "Use MCP database tools to first inspect the schema, then EXECUTE AGGREGATED QUERIES to reduce volume. "
                "Return per-cycle aggregates for the requested station: "
                "Example of query try to use avg because it will reduce the volume of data you need to fetch: SELECT cycle_number AS cycle, AVG(temp) AS temp, AVG(psal) AS psal FROM measurements JOIN profiles ON profiles.profile_id = measurements.profile_id "
                "WHERE profiles.platform_number = 19005 GROUP BY cycle_number ORDER BY cycle_number; this is only example "
                "Also return a small sample of distinct latitude/longitude pairs for mapping (e.g., first 3 cycles) and any needed timestamps."
                "Output must be structured tabular results with clear field names."
            ),
            agent=data_retrieval,
            expected_output="A concise structured dataset containing all fields needed to satisfy the user's request.",
            context=[understand_request],
            tools=[*tools]
        )

        external_geolocation_search = Task(
            description="Use SerperDevTool with VERY SPECIFIC queries to fetch precise latitude/longitude for the identified ocean regions. Limit to 1-2 searches. Return exact coordinates only.You must use the tools available to you to get the data you need.",
            agent=data_retrieval,
            expected_output="Exact lat/lng for each requested region.You must use the tools available to you to get the data you need.",
            context=[understand_request],
            tools=[SerperDevTool()]
        )

        result_maker = Task(
            description=(
                "Generate ONLY the final JSON (no markdown). STRICTLY follow FinalOutputModel and this format: "
                "report.title, report.content; graphs MUST include: "
                "1) line 'Temperature Over Cycles' with xKey='cycle', yKey='temp'; "
                "2) line 'Salinity Over Cycles' with xKey='cycle', yKey='psal'; "
                "3) scatter 'Temperature vs Salinity' with xKey='temp', yKey='psal'. "
                "Use aggregated per-cycle averages for lines. Data objects MUST include keys matching xKey/yKey; no empty objects; keep each graph <= 200 points. "
                "maps should include at least one 'labels' map with lat/lng points for station cycles; optionally include 'hexbin' or 'heatmap'. "
                "All numbers must be numeric; lat in [-90,90], lng in [-180,180]. Do not add extra keys."
            ),
            agent=data_analyst,
            context=[understand_request, database_query, external_geolocation_search],
            output_json=FinalOutputModel,
            expected_output="A single JSON object formatted as per FinalOutputModel with no additional text."
        )

        crew = Crew(
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

        if verbose:
            print("🚀 Starting CrewAI execution with simplified 3-agent architecture...")
            print(f"📊 Available MCP tools: {[tool.name for tool in tools]}")
            print(f"🔧 Process: Sequential (Gemini compatible)")
            print(f"🔑 Gemini API Key: {'✅ Set' if os.getenv('GEMINI_API_KEY') else '❌ Missing'}")
            print("=" * 60)

        result = crew.kickoff(input_data)

        # Parse raw JSON output; strip ```json fences if present
        if isinstance(result, BaseModel):
            return result.model_dump()
        if isinstance(result, dict):
            return result
        # Treat as string and sanitize fenced blocks
        text = str(result)
        clean_text = re.sub(r"```json\n?|\n?```", "", text).strip()
        return json.loads(clean_text)


if __name__ == "__main__":
    demo_query = "Show me the temperature and salinity data in the indian ocean for the station no. 19005"
    try:
        output = run_crewai_pipeline(demo_query, verbose=True)
        print("\n📋 FINAL RESULT:\n", json.dumps(output, indent=2))
    except Exception as e:
        print(f"\n❌ CREW EXECUTION FAILED: {e}")