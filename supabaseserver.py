#!/usr/bin/env python3
"""
MCP Server for Supabase PostgreSQL Database Querying
Provides tools to query Supabase database using natural language
"""

import json
import re
from typing import Optional
from fastmcp import FastMCP
from langchain_community.utilities import SQLDatabase
import psycopg2
from psycopg2.extras import RealDictCursor
import os

# Supabase configuration (hardcoded Session/Transaction Pooler as requested)
# Note: Transaction pooler (port 6543) does not support PREPARE statements.
# Replace PASSWORD with your actual password.

SUPABASE_DB_USER = "postgres.hbfmvzzjbvqzmwpxnrcb"
SUPABASE_DB_PASSWORD = "Suryansh@1440"
SUPABASE_DB_HOST = "aws-1-ap-south-1.pooler.supabase.com"
SUPABASE_DB_PORT = 6543
SUPABASE_DB_NAME = "postgres"
SUPABASE_SSLMODE = "require"

def _get_connection_params() -> dict:
    """Return psycopg2 connection params using hardcoded Supabase pooler settings."""
    return {
        "user": SUPABASE_DB_USER,
        "password": SUPABASE_DB_PASSWORD,
        "host": SUPABASE_DB_HOST,
        "port": SUPABASE_DB_PORT,
        "dbname": SUPABASE_DB_NAME,
        "sslmode": SUPABASE_SSLMODE,
    }

# Global database connection
db: Optional[SQLDatabase] = None
postgres_conn = None

def connect_database() -> None:
    """Initialize database connection to Supabase PostgreSQL."""
    global db, postgres_conn
    try:
        # Connect to Supabase PostgreSQL
        params = _get_connection_params()
        postgres_conn = psycopg2.connect(**params)
        print(f"Connected to database '{params['dbname']}' at {params['host']}:{params['port']} with sslmode={params['sslmode']}")
        
        # Test the connection by getting table names
        try:
            cursor = postgres_conn.cursor()
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            if tables:
                print(f"Successfully connected to Supabase database")
                print(f"Found tables: {tables}")
            else:
                print(f"Successfully connected to Supabase database")
                print("No tables found in database")
                
        except Exception as e:
            print(f"Error testing Supabase connection: {e}")
            raise
            
    except Exception as e:
        print(f"Failed to connect to Supabase database: {e}")
        raise

# Initialize MCP server
mcp = FastMCP("Supabase Database Server")

def _process_reserved_keywords(sql_query: str) -> str:
    """
    Process SQL query to handle PostgreSQL reserved keywords by adding quotes.
    Also handles malformed quotes that might occur during MCP communication.
    """
    # List of common PostgreSQL reserved keywords that might be table names
    reserved_keywords = [
        'user', 'order', 'group', 'select', 'from', 'where', 'table', 'index',
        'view', 'schema', 'database', 'column', 'constraint', 'trigger', 'function',
        'procedure', 'sequence', 'type', 'domain', 'rule', 'default', 'check',
        'foreign', 'primary', 'unique', 'references', 'cascade', 'restrict',
        'grant', 'revoke', 'privilege', 'role', 'user', 'public', 'private'
    ]
    
    import re
    
    # First, fix any malformed quotes (like "user instead of "user")
    # Pattern to match malformed quotes: "table_name without closing quote
    malformed_quote_pattern = r'"([a-zA-Z_][a-zA-Z0-9_]*)(?![a-zA-Z0-9_"])(?=\s|$)'
    def fix_malformed_quotes(match):
        table_name = match.group(1)
        return f'"{table_name}"'
    
    processed_query = re.sub(malformed_quote_pattern, fix_malformed_quotes, sql_query)
    
    # Then, add quotes to unquoted reserved keywords
    # Pattern to match FROM table_name (case insensitive)
    from_pattern = r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)\b'
    
    def quote_table_name(match):
        table_name = match.group(1).lower()
        if table_name in reserved_keywords:
            return f'FROM "{table_name}"'
        return match.group(0)
    
    processed_query = re.sub(from_pattern, quote_table_name, processed_query, flags=re.IGNORECASE)
    
    return processed_query

@mcp.tool
async def execute_sql(sql_query: str) -> str:
    """
    Execute a SELECT SQL query on the database. Only SELECT queries are allowed for security.
    
    Input: sql_query (string) - The SELECT SQL query to execute (e.g., "SELECT * FROM users", "SELECT name, age FROM users WHERE age > 25")
        
    Returns:
        str: Query results
    """
    try:
        if postgres_conn is None:
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
        
        # Process the query to handle reserved keywords
        processed_query = _process_reserved_keywords(sql_query)
        
        # Execute the SQL query using PostgreSQL
        cursor = postgres_conn.cursor(cursor_factory=RealDictCursor)
        try:
            tried_notes = []
            cursor.execute(processed_query)
            
            # Format the response
            response_text = f"SQL Query: {sql_query}\n\n"
            
            try:
                rows = cursor.fetchall()
                if rows:
                    # Convert RealDictRow to regular dict for JSON serialization
                    # Handle datetime objects by converting them to strings
                    rows_data = []
                    for row in rows:
                        row_dict = {}
                        for key, value in dict(row).items():
                            if hasattr(value, 'isoformat'):  # datetime objects
                                row_dict[key] = value.isoformat()
                            else:
                                row_dict[key] = value
                        rows_data.append(row_dict)
                    response_text += f"Results:\n{json.dumps(rows_data, indent=2)}"
                else:
                    response_text += "Query executed successfully (no rows returned)"
            except Exception as e:
                response_text += f"Error fetching results: {str(e)}"
            
            # Commit the transaction
            postgres_conn.commit()
            if tried_notes:
                response_text += "\n\n/* tried: " + "; ".join(tried_notes) + " */"
            return response_text
            
        except Exception as e:
            postgres_conn.rollback()
            raise e
        finally:
            cursor.close()
        
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
        if postgres_conn is None:
            return "Database not connected. Please connect first."
        
        cursor = postgres_conn.cursor()
        try:
            # Get all tables in public schema
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            schema_info = "Database Schema:\n\n"
            
            for table in tables:
                # Get table structure
                cursor.execute("""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                    ORDER BY ordinal_position
                """, (table,))
                
                columns = []
                for row in cursor.fetchall():
                    col_name = row[0]
                    col_type = row[1]
                    is_nullable = "NULL" if row[2] == 'YES' else "NOT NULL"
                    col_default = f" DEFAULT {row[3]}" if row[3] else ""
                    max_length = f"({row[4]})" if row[4] else ""
                    
                    columns.append(f"  {col_name} {col_type}{max_length} {is_nullable}{col_default}".strip())
                
                # Get primary key information
                cursor.execute("""
                    SELECT column_name
                    FROM information_schema.key_column_usage
                    WHERE table_schema = 'public'
                    AND table_name = %s
                    AND constraint_name IN (
                        SELECT constraint_name
                        FROM information_schema.table_constraints
                        WHERE table_schema = 'public'
                        AND table_name = %s
                        AND constraint_type = 'PRIMARY KEY'
                    )
                """, (table, table))
                
                primary_keys = [row[0] for row in cursor.fetchall()]
                
                schema_info += f"CREATE TABLE {table} (\n"
                schema_info += ",\n".join(columns)
                if primary_keys:
                    schema_info += f",\n  PRIMARY KEY ({', '.join(primary_keys)})"
                schema_info += "\n);\n\n"
                
                # Get sample data
                try:
                    cursor.execute(f'SELECT * FROM "{table}" LIMIT 3')
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
            
            postgres_conn.commit()
            return schema_info
            
        except Exception as e:
            postgres_conn.rollback()
            raise e
        finally:
            cursor.close()
        
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
        if postgres_conn is None:
            return "Database not connected. Please connect first."
        
        cursor = postgres_conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
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
        if postgres_conn is None:
            return "Database not connected. Please connect first."
        
        cursor = postgres_conn.cursor()
        
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        relationship_info = "Table Relationships:\n\n"
        
        for table in tables:
            # Get foreign key information
            cursor.execute("""
                SELECT 
                    tc.constraint_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'public'
                AND tc.table_name = %s
            """, (table,))
            
            foreign_keys = cursor.fetchall()
            
            if foreign_keys:
                relationship_info += f"Table '{table}' has foreign keys:\n"
                for fk in foreign_keys:
                    relationship_info += f"  - {fk[1]} -> {fk[2]}.{fk[3]}\n"
                relationship_info += "\n"
            else:
                relationship_info += f"Table '{table}' has no foreign key relationships.\n\n"
        
        # Also check for common patterns (like user_id columns)
        relationship_info += "Potential relationships based on column names:\n"
        for table in tables:
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = %s
            """, (table,))
            
            columns = [row[0] for row in cursor.fetchall()]
            for col_name in columns:
                if col_name.endswith('_id') and col_name != 'id':
                    referenced_table = col_name[:-3]  # Remove '_id' suffix
                    if referenced_table in tables:
                        relationship_info += f"  - {table}.{col_name} likely references {referenced_table}.id\n"
        
        cursor.close()
        return relationship_info
        
    except Exception as e:
        return f"Error getting table relationships: {str(e)}"

@mcp.tool
async def describe_table(table_name: str) -> str:
    """
    Get detailed information about a specific table including columns and types.
    
    Input: table_name (string) - Name of the table to describe (e.g., "users", "products", "orders")
        
    Returns:
        str: Table structure information
    """
    try:
        if postgres_conn is None:
            return "Database not connected. Please connect first."
        
        cursor = postgres_conn.cursor()
        
        # Get table structure
        cursor.execute("""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))
        
        columns = []
        for row in cursor.fetchall():
            col_name = row[0]
            col_type = row[1]
            is_nullable = "NULL" if row[2] == 'YES' else "NOT NULL"
            col_default = f" DEFAULT {row[3]}" if row[3] else ""
            max_length = f"({row[4]})" if row[4] else ""
            
            columns.append(f"  {col_name} {col_type}{max_length} {is_nullable}{col_default}".strip())
        
        # Get primary key information
        cursor.execute("""
            SELECT column_name
            FROM information_schema.key_column_usage
            WHERE table_schema = 'public'
            AND table_name = %s
            AND constraint_name IN (
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_schema = 'public'
                AND table_name = %s
                AND constraint_type = 'PRIMARY KEY'
            )
        """, (table_name, table_name))
        
        primary_keys = [row[0] for row in cursor.fetchall()]
        
        table_info = f"Table '{table_name}' structure:\n\n"
        table_info += f"CREATE TABLE {table_name} (\n"
        table_info += ",\n".join(columns)
        if primary_keys:
            table_info += f",\n  PRIMARY KEY ({', '.join(primary_keys)})"
        table_info += "\n);\n\n"
        
        # Get sample data
        try:
            cursor.execute(f'SELECT * FROM "{table_name}" LIMIT 3')
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
        
        cursor.close()
        return table_info
        
    except Exception as e:
        return f"Error describing table '{table_name}': {str(e)}"

def main():
    """Main function to start the server."""
    # Connect to database
    connect_database()
    
    # Run the MCP server
    mcp.run()

if __name__ == "__main__":
    main()
