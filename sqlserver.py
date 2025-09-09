#!/usr/bin/env python3
"""
MCP Server for SQL Database Querying
Provides tools to query Turso database using natural language
"""

import json
import re
from typing import Optional
from fastmcp import FastMCP
from langchain_community.utilities import SQLDatabase
import sqlite3
import os
import libsql

# Turso Configuration
TURSO_URL = "libsql://sihtest-surya1440.aws-ap-south-1.turso.io"
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3NTcyMjQwNDYsImlkIjoiNmIyYzhkYjctOTM5NS00OTRiLThkZDctMzc1ZjBlOWI2YTVlIiwicmlkIjoiZTQ2NTgwZTgtNThiMC00ZmIxLWI5MDAtODY4ZjBkZjc2YWExIn0.uEPsMaN7Zbyzaza4R6s2YommzGrmwwpHQAGlJxA4V7dGR9ddSYfOzraruKQ1SIf0nroXiFoQEFT34gxt_qCuDg"

# Global database connection
db: Optional[SQLDatabase] = None
libsql_client = None

def connect_database() -> None:
    """Initialize database connection to Turso using embedded replica."""
    global db, libsql_client
    try:
        # Create local SQLite database and sync with Turso
        local_db_path = "turso_local.db"
        libsql_client = libsql.connect(
            local_db_path, 
            sync_url=TURSO_URL, 
            auth_token=TURSO_TOKEN
        )
        
        # Sync with remote database
        libsql_client.sync()
        
        # Test the connection by getting table names
        try:
            cursor = libsql_client.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            if tables:
                print(f"Successfully connected to Turso database: {TURSO_URL}")
                print(f"Found tables: {tables}")
            else:
                print(f"Successfully connected to Turso database: {TURSO_URL}")
                print("No tables found in database")
                
        except Exception as e:
            print(f"Error testing Turso connection: {e}")
            raise
            
    except Exception as e:
        print(f"Failed to connect to Turso database: {e}")
        raise

# Initialize MCP server
mcp = FastMCP("SQL Database Server")

@mcp.tool
async def execute_sql(sql_query: str) -> str:
    """
    Execute a SELECT SQL query on the database. Only SELECT queries are allowed for security.
    
    Input: sql_query (string) - The SELECT SQL query to execute (e.g., "SELECT * FROM user", "SELECT name, age FROM user WHERE age > 25")
        
    Returns:
        str: Query results
    """
    try:
        if libsql_client is None:
            return "Database not connected. Please connect first."
        
        # Security check: Only allow SELECT queries
        sql_query_upper = sql_query.strip().upper()
        if not sql_query_upper.startswith('SELECT'):
            return f"Error: Only SELECT queries are allowed for security. Your query '{sql_query}' is not permitted."
        
        # Additional security checks for dangerous keywords
        dangerous_keywords = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'TRUNCATE', 'EXEC', 'EXECUTE']
        for keyword in dangerous_keywords:
            if keyword in sql_query_upper:
                return f"Error: The keyword '{keyword}' is not allowed for security reasons. Only SELECT queries are permitted."
        
        # Execute the SQL query using libsql client
        cursor = libsql_client.cursor()
        cursor.execute(sql_query)
        
        # Format the response
        response_text = f"SQL Query: {sql_query}\n\n"
        
        try:
            rows = cursor.fetchall()
            if rows:
                # Get column names
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows_data = []
                for row in rows:
                    row_dict = {}
                    for i, value in enumerate(row):
                        col_name = columns[i] if i < len(columns) else f"column_{i}"
                        row_dict[col_name] = value
                    rows_data.append(row_dict)
                
                response_text += f"Results:\n{json.dumps(rows_data, indent=2)}"
            else:
                response_text += "Query executed successfully (no rows returned)"
        except Exception as e:
            response_text += f"Error fetching results: {str(e)}"
        
        return response_text
        
    except Exception as e:
        return f"Error executing SQL query: {str(e)}"

@mcp.tool
async def get_database_schema() -> str:
    """
    Get the database schema information including all tables and columns.
    
    Input: No input required - just call the function
    
    Returns:
        str: Database schema information
    """
    try:
        if libsql_client is None:
            return "Database not connected. Please connect first."
        
        # Get all tables
        cursor = libsql_client.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        schema_info = "Database Schema:\n\n"
        
        for table in tables:
            # Get table structure
            cursor.execute(f"PRAGMA table_info({table})")
            columns = []
            for row in cursor.fetchall():
                col_name = row[1]  # column name
                col_type = row[2]  # column type
                not_null = "NOT NULL" if row[3] else ""
                primary_key = "PRIMARY KEY" if row[5] else ""
                columns.append(f"  {col_name} {col_type} {not_null} {primary_key}".strip())
            
            schema_info += f"CREATE TABLE {table} (\n"
            schema_info += ",\n".join(columns)
            schema_info += "\n);\n\n"
            
            # Get sample data
            try:
                cursor.execute(f"SELECT * FROM {table} LIMIT 3")
                sample_rows = cursor.fetchall()
                if sample_rows:
                    schema_info += f"/*\nSample data from {table}:\n"
                    # Add column headers
                    if cursor.description:
                        headers = [desc[0] for desc in cursor.description]
                        schema_info += "\t".join(headers) + "\n"
                    # Add sample rows
                    for row in sample_rows:
                        schema_info += "\t".join(str(val) for val in row) + "\n"
                    schema_info += "*/\n\n"
            except:
                pass  # Skip sample data if there's an error
        
        return schema_info
        
    except Exception as e:
        return f"Error getting database schema: {str(e)}"

@mcp.tool
async def get_table_names() -> str:
    """
    Get list of all table names in the database.
    
    Input: No input required - just call the function
    
    Returns:
        str: List of table names
    """
    try:
        if libsql_client is None:
            return "Database not connected. Please connect first."
        
        cursor = libsql_client.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        return f"Available tables: {', '.join(tables)}"
        
    except Exception as e:
        return f"Error getting table names: {str(e)}"

@mcp.tool
async def get_table_relationships() -> str:
    """
    Get information about how tables are connected through foreign keys and relationships.
    
    Input: No input required - just call the function
    
    Returns:
        str: Table relationship information
    """
    try:
        if libsql_client is None:
            return "Database not connected. Please connect first."
        
        cursor = libsql_client.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        
        relationship_info = "Table Relationships:\n\n"
        
        for table in tables:
            # Get foreign key information
            cursor.execute(f"PRAGMA foreign_key_list({table})")
            foreign_keys = cursor.fetchall()
            
            if foreign_keys:
                relationship_info += f"Table '{table}' has foreign keys:\n"
                for fk in foreign_keys:
                    relationship_info += f"  - {fk[3]} -> {fk[2]}.{fk[4]}\n"
                relationship_info += "\n"
            else:
                relationship_info += f"Table '{table}' has no foreign key relationships.\n\n"
        
        # Also check for common patterns (like user_id columns)
        relationship_info += "Potential relationships based on column names:\n"
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            for col in columns:
                col_name = col[1]
                if col_name.endswith('_id') and col_name != 'id':
                    referenced_table = col_name[:-3]  # Remove '_id' suffix
                    if referenced_table in tables:
                        relationship_info += f"  - {table}.{col_name} likely references {referenced_table}.id\n"
        
        return relationship_info
        
    except Exception as e:
        return f"Error getting table relationships: {str(e)}"

@mcp.tool
async def describe_table(table_name: str) -> str:
    """
    Get detailed information about a specific table including columns and types.
    
    Input: table_name (string) - Name of the table to describe (e.g., "user", "products", "orders")
        
    Returns:
        str: Table structure information
    """
    try:
        if libsql_client is None:
            return "Database not connected. Please connect first."
        
        # Get table structure
        cursor = libsql_client.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = []
        for row in cursor.fetchall():
            col_name = row[1]  # column name
            col_type = row[2]  # column type
            not_null = "NOT NULL" if row[3] else ""
            primary_key = "PRIMARY KEY" if row[5] else ""
            columns.append(f"  {col_name} {col_type} {not_null} {primary_key}".strip())
        
        table_info = f"Table '{table_name}' structure:\n\n"
        table_info += f"CREATE TABLE {table_name} (\n"
        table_info += ",\n".join(columns)
        table_info += "\n);\n\n"
        
        # Get sample data
        try:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
            sample_rows = cursor.fetchall()
            if sample_rows:
                table_info += f"/*\nSample data from {table_name}:\n"
                # Add column headers
                if cursor.description:
                    headers = [desc[0] for desc in cursor.description]
                    table_info += "\t".join(headers) + "\n"
                # Add sample rows
                for row in sample_rows:
                    table_info += "\t".join(str(val) for val in row) + "\n"
                table_info += "*/\n"
        except:
            pass  # Skip sample data if there's an error
        
        return table_info
        
    except Exception as e:
        return f"Error describing table '{table_name}': {str(e)}"

def main():
    """Main function to start the server."""
    # Connect to database
    connect_database()
    
    # Run the MCP server with HTTP transport
    mcp.run()

if __name__ == "__main__":
    main()