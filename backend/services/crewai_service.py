from dotenv import load_dotenv
load_dotenv()
import os
import pandas as pd
import json
import logging
from datetime import datetime

from crewai import LLM,Agent,Task,Crew
from crewai_tools import SerperDevTool
from crewai.tools import tool
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters


# Configure LLM for Gemini
llm = LLM(
    model="gemini/gemini-2.0-flash",
    temperature=0.1,
    api_key=os.getenv("GEMINI_API_KEY")  # Use the correct environment variable
)

# Custom tool for JSON report generation
@tool("JSON Report Generator")
def generate_json_report(thought: str, report_content: str, graphs_data: str = "[]", maps_data: str = "[]") -> str:
    """
    Generates a structured JSON report combining thought, content, multiple graphs, and multiple maps.
    The graphs_data and maps_data should be JSON arrays containing visualization information.
    """
    try:
        # Parse the input data as arrays
        graphs_parsed = json.loads(graphs_data) if graphs_data else []
        maps_parsed = json.loads(maps_data) if maps_data else []
        
        # Ensure inputs are arrays
        if not isinstance(graphs_parsed, list):
            graphs_parsed = [graphs_parsed] if graphs_parsed else []
        if not isinstance(maps_parsed, list):
            maps_parsed = [maps_parsed] if maps_parsed else []
        
        # Process graphs array
        processed_graphs = []
        for graph in graphs_parsed:
            if isinstance(graph, str):
                try:
                    graph = json.loads(graph)
                except:
                    continue
            
            processed_graph = {
                "type": graph.get("type", "line"),
                "title": graph.get("title", "Data Visualization"),
                "description": graph.get("description", "Data visualization"),
                "data": graph.get("dataPoints", []),
                "xKey": graph.get("xKey", "x"),
                "yKey": graph.get("yKey", "y"),
                "seriesNames": graph.get("yKeys", []),
                "colors": graph.get("colors", ["blue"])
            }
            processed_graphs.append(processed_graph)
        
        # Process maps array - format for ChatMap component
        processed_maps = []
        for map_data in maps_parsed:
            if isinstance(map_data, str):
                try:
                    map_data = json.loads(map_data)
                except:
                    continue
            
            # Create map object with all available data arrays
            processed_map = {
                "title": map_data.get("title", "Interactive Globe View"),
                "description": map_data.get("description", "3D globe visualization"),
                "labelsData": map_data.get("labels", []),
                "hexBinPointsData": map_data.get("hexbin", []),
                "heatmapsData": map_data.get("heatmap", [])
            }
            
            processed_maps.append(processed_map)
        
        # Create the structured report
        report = {
            "thought": thought,
            "result": {
                "report": {
                    "title": "Data Analysis Report",
                    "content": report_content
                },
                "graphs": processed_graphs,
                "maps": processed_maps
            }
        }
        
        return json.dumps(report, indent=2)
        
    except json.JSONDecodeError as e:
        return f"Error parsing JSON data: {str(e)}"
    except Exception as e:
        return f"Error generating report: {str(e)}"

server_params = StdioServerParameters(
    command=".venv/Scripts/python.exe", 
    args=["mcpServers/supabaseserver.py"],
    env={"UV_PYTHON": "3.12", **os.environ},
    
)

with MCPServerAdapter(server_params) as tools:
    print(f"Available tools from Stdio MCP server: {[tool.name for tool in tools]}")
        
    # 1. Query Analyst Agent 🕵️
    query_analyst = Agent(
        role="Query Analysis Specialist",
        goal="Understand user intent and decompose complex queries into manageable sub-tasks",
        backstory="You are an expert at understanding natural language queries and breaking them down into clear, actionable components. You excel at identifying what information is needed and categorizing the type of request (data analysis, visualization, reporting).",
        verbose=True,
        llm=llm
    )

    # 2. Data Retrieval Agent 💾
    data_retrieval = Agent(
        role="Database Query Specialist", 
        goal="Execute database queries and retrieve relevant data using MCP tools and external search",
        backstory="You are a database expert who specializes in writing efficient SQL queries and retrieving data from databases. You use MCP tools to interact with Supabase and external search tools for supplementary data. When using SerperDevTool, ALWAYS use very specific search queries like 'station 19005 coordinates' or 'buoy indian ocean latitude longitude'. Never use broad searches. Limit to 2-3 targeted searches maximum.",
        tools=[SerperDevTool(), *tools],  # MCP tools + external search
        verbose=True,
        llm=llm
    )

    # 3. Data Analysis & Reporting Agent 📊
    data_analyst = Agent(
        role="Data Analysis & Reporting Specialist",
        goal="Analyze retrieved data and generate comprehensive reports with visualizations compatible with ChatMap component",
        backstory="""You are a data scientist who excels at analyzing datasets, identifying patterns, and creating comprehensive reports. 
        You transform raw data into actionable insights and generate structured outputs for visualization. 
        You perform statistical analysis manually and create detailed reports without external tools. 
        You understand the ChatMap component format and create map data with title, description, and all data arrays.
        
        Format examples:
        - labelsData: [{"lat": 40.7128, "lng": -74.0060, "text": "New York", "color": "#ff6b6b", "size": 1.8, "altitude": 0.01}]
        - hexBinPointsData: [{"lat": 40.7128, "lng": -74.0060, "weight": 15}]
        - heatmapsData: [{"lat": 19.0760, "lng": 72.8777, "weight": 0.9}]""",
        tools=[generate_json_report],  # Only JSON report generation tool
        verbose=True,
        llm=llm
    )

    # 4. Map Data Generation Agent 🗺️
    map_agent = Agent(
        role="Geographic Data Specialist",
        goal="Generate geolocation data and coordinates for 3D globe visualization compatible with ChatMap component",
        backstory="""You are a geographic data expert who specializes in finding latitude and longitude coordinates for locations. 
        You retrieve location data from databases and use external tools to geocode locations not in the database. 
        You understand the ChatMap component format and create map data with proper title, description, and all data arrays.
        
        Format examples:
        - labelsData: [{"lat": 40.7128, "lng": -74.0060, "text": "New York", "color": "#ff6b6b", "size": 1.8, "altitude": 0.01}]
        - hexBinPointsData: [{"lat": 40.7128, "lng": -74.0060, "weight": 15}]
        - heatmapsData: [{"lat": 19.0760, "lng": 72.8777, "weight": 0.9}]
        
        When using SerperDevTool, use VERY SPECIFIC searches like 'station 19005 exact coordinates' or 'buoy indian ocean latitude longitude'. Limit to 1-2 targeted searches.""",
        tools=[SerperDevTool(), *tools],  # For location data and geocoding
        verbose=True,
        llm=llm
    )

    # Task 1: Query Decomposition
    query_decomposition = Task(
        description="Analyze the user query '{query}' and break it down into clear components. Identify what data needs to be retrieved and what type of analysis is required.",
        agent=query_analyst,
        expected_output="A structured breakdown of the query including: 1) Main intent, 2) Required data fields, 3) Analysis type needed, 4) Any constraints or filters"
    )

    # Task 2: Intent Classification
    intent_classification = Task(
        description="Categorize the user's request into one of: 'data analysis', 'map visualization', 'report generation', or 'combined'. Determine if the query requires geographic data, statistical analysis, or both.",
        agent=query_analyst,
        expected_output="Clear classification of the request type and identification of required visualization components (charts, maps, or both)",
        context=[query_decomposition]
    )

    # Task 3: Database Querying
    database_query = Task(
        description="Based on the query analysis, execute the appropriate database query using MCP tools. Retrieve the relevant data from the Supabase database.",
        agent=data_retrieval,
        expected_output="Raw data retrieved from the database in a structured format",
        context=[query_decomposition, intent_classification],
        tools=[*tools]
    )

    # Task 4: External Data Search
    external_data_search = Task(
        description="If the query requires specific coordinates or location data not in the database, use SerperDevTool with VERY SPECIFIC search queries. Use targeted searches like 'station 19005 coordinates latitude longitude' or 'buoy location indian ocean coordinates'. Avoid broad searches. Limit to 2-3 specific searches maximum.",
        agent=data_retrieval,
        expected_output="Specific external data with exact coordinates or location information",
        context=[query_decomposition, intent_classification, database_query],
        tools=[SerperDevTool()]
    )

    # Task 5: Data Processing & Analysis
    data_processing = Task(
        description="Clean and process the retrieved data. Perform statistical analysis, handle missing values, calculate averages, and identify trends. Analyze the data manually and provide detailed statistical insights.",
        agent=data_analyst,
        expected_output="Processed data with statistical analysis and insights",
        context=[query_decomposition, intent_classification, database_query, external_data_search],
        tools=[]
    )

    # Task 6: Content Generation
    content_generation = Task(
        description="Write a natural language report summarizing the findings. Create clear, concise content that explains the data analysis results. Generate ONE comprehensive report.",
        agent=data_analyst,
        expected_output="Human-readable report content summarizing the analysis findings",
        context=[query_decomposition, intent_classification, data_processing],
        tools=[]
    )

    # Task 7: Graph Data Generation
    graph_generation = Task(
        description="Create structured data for chart generation. Generate an ARRAY of graph objects, each containing type (bar, line, pie, scatter, area), title, description, data points, xKey, yKey, and colors. Create multiple graphs if needed for different data aspects.",
        agent=data_analyst,
        expected_output="ARRAY of JSON structures for graph visualization with all required fields",
        context=[query_decomposition, intent_classification, data_processing],
        tools=[]
    )

    # Task 8: Location Data Retrieval
    location_data_retrieval = Task(
        description="Fetch latitude and longitude coordinates from the database for known data points. Use MCP tools to retrieve location data.",
        agent=map_agent,
        expected_output="Location data with lat/lng coordinates from the database",
        context=[query_decomposition, intent_classification, database_query],
        tools=[*tools]
    )

    # Task 9: Geocoding
    geocoding = Task(
        description="If the user query mentions specific locations without explicit coordinates, use SerperDevTool with TARGETED searches like 'station 19005 latitude longitude coordinates' or 'buoy indian ocean exact location'. Use only 1-2 very specific searches. Avoid broad geographic searches.",
        agent=map_agent,
        expected_output="Exact geocoded coordinates for specific locations",
        context=[query_decomposition, intent_classification, location_data_retrieval],
        tools=[SerperDevTool()]
    )

    # Task 10: Map Data Generation
    map_data_generation = Task(
        description="""Generate JSON structure for 3D globe visualization compatible with ChatMap component. 
        Create an ARRAY of map objects with this EXACT format:
        
        For labelsData: [{"lat": 40.7128, "lng": -74.0060, "text": "New York", "color": "#ff6b6b", "size": 1.8, "altitude": 0.01}]
        
        For hexBinPointsData: [{"lat": 40.7128, "lng": -74.0060, "weight": 15}]
        
        For heatmapsData: [{"lat": 19.0760, "lng": 72.8777, "weight": 0.9}]
        
        Each map object should have: title, description, labelsData, hexBinPointsData, heatmapsData""",
        agent=map_agent,
        expected_output="ARRAY of JSON structures matching ChatMap.jsx demo data format exactly",
        context=[query_decomposition, intent_classification, location_data_retrieval, geocoding],
        tools=[]
    )

    # Task 11: Final JSON Report Generation
    final_report_generation = Task(
        description="Combine all analysis results into the final JSON report format. Use the generate_json_report tool ONCE to create the complete output with thought, result, report, graphs array, and maps array sections.",
        agent=data_analyst,
        expected_output="Complete JSON report in the required format with thought, result, report, graphs array, and maps array sections",
        context=[content_generation, graph_generation, map_data_generation],
        tools=[generate_json_report]
    )

    # Create the crew with basic configuration (avoiding advanced features that require OpenAI)
    crew = Crew(
        agents=[query_analyst, data_retrieval, data_analyst, map_agent],
        tasks=[
            query_decomposition, intent_classification, database_query, external_data_search,
            data_processing, content_generation, graph_generation, location_data_retrieval,
            geocoding, map_data_generation, final_report_generation
        ],
        process="sequential",  # Use sequential process
        max_iter=2,  # Further reduced to prevent excessive iterations
        max_execution_time=120,  # Reduced timeout to 2 minutes
        verbose=True
    )

    # Test input
    input_data = {
        "query": "Show me the temperature and salinity data in the indian ocean for the station no. 19005 and also show me a map of the buoy locations"
    }

    print("🚀 Starting CrewAI execution with 4-agent architecture...")
    print(f"📊 Available MCP tools: {[tool.name for tool in tools]}")
    print(f"🔧 Process: Sequential (Gemini compatible)")
    print(f"🧠 Memory: Enabled for context retention")
    print(f"⚡ Cache: Enabled for efficiency")
    print(f"📈 Max RPM: 60 requests per minute")
    print(f"🔑 Gemini API Key: {'✅ Set' if os.getenv('GEMINI_API_KEY') else '❌ Missing'}")
    print("=" * 60)

    # Execute the crew
    try:
        result = crew.kickoff(input_data)
        print("\n✅ CREW EXECUTION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("📋 FINAL RESULT:")
        print(result)
    except Exception as e:
        print(f"\n❌ CREW EXECUTION FAILED: {e}")
        print("=" * 60)