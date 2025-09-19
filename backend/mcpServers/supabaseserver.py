#!/usr/bin/env python3
"""
MCP Server for Supabase PostgreSQL Database Querying
Provides tools to query Supabase database using natural language
"""

import json
import re
from fastmcp import FastMCP
import psycopg2
from psycopg2.extras import RealDictCursor


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
postgres_conn = None

def connect_database() -> None:
    """Initialize database connection to Supabase PostgreSQL."""
    global postgres_conn
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



# functions help to fetch tables, columns, primary keys, relationships, and small samples.
def _fetch_tables(cursor):
    cursor.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """
    )
    return [row[0] for row in cursor.fetchall()]

def _fetch_columns_for_tables(cursor, tables):
    if not tables:
        return {}
    cursor.execute(
        """
        SELECT c.table_name,
               c.column_name,
               c.data_type,
               c.is_nullable,
               c.column_default,
               c.character_maximum_length,
               c.ordinal_position
        FROM information_schema.columns c
        WHERE c.table_schema = 'public'
          AND c.table_name = ANY(%s)
        ORDER BY c.table_name, c.ordinal_position
        """,
        (tables,)
    )
    result = {}
    for (
        table_name,
        column_name,
        data_type,
        is_nullable,
        column_default,
        character_maximum_length,
        ordinal_position,
    ) in cursor.fetchall():
        cols = result.setdefault(table_name, [])
        max_length = f"({character_maximum_length})" if character_maximum_length else ""
        nullable = "NULL" if is_nullable == 'YES' else "NOT NULL"
        default = f" DEFAULT {column_default}" if column_default else ""
        cols.append(f"  {column_name} {data_type}{max_length} {nullable}{default}".strip())
    return result

def _fetch_primary_keys_for_tables(cursor, tables):
    if not tables:
        return {}
    cursor.execute(
        """
        SELECT kcu.table_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        WHERE tc.table_schema = 'public'
          AND tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_name = ANY(%s)
        ORDER BY kcu.table_name, kcu.ordinal_position
        """,
        (tables,)
    )
    pks = {}
    for table_name, column_name in cursor.fetchall():
        cols = pks.setdefault(table_name, [])
        cols.append(column_name)
    return pks

def _fetch_foreign_keys_for_tables(cursor, tables):
    if not tables:
        return {}
    cursor.execute(
        """
        SELECT
          tc.table_name AS table_name,
          kcu.column_name AS column_name,
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
          AND tc.table_name = ANY(%s)
        ORDER BY tc.table_name, kcu.ordinal_position
        """,
        (tables,)
    )
    fks = {}
    for table_name, column_name, foreign_table_name, foreign_column_name in cursor.fetchall():
        lst = fks.setdefault(table_name, [])
        lst.append((column_name, foreign_table_name, foreign_column_name))
    return fks

@mcp.tool
async def get_database_schema() -> str:
    """
    Get complete database schema: tables, columns, primary keys, relationships, and small samples.
    
    Input: No input required - just call the function
    
    Returns:
        str: Detailed schema information for all public tables, including relationships.
    """
    try:
        if postgres_conn is None:
            return "Database not connected. Please connect first."
        
        cursor = postgres_conn.cursor()
        try:
            tables = _fetch_tables(cursor)
            cols_map = _fetch_columns_for_tables(cursor, tables)
            pk_map = _fetch_primary_keys_for_tables(cursor, tables)
            fks_map = _fetch_foreign_keys_for_tables(cursor, tables)

            schema_info = "Database Schema (public):\n\n"
            schema_info += "Tables: " + ", ".join(tables) + "\n\n"
            
            for table in tables:
                # Describe table (columns + PKs)
                columns = cols_map.get(table, [])
                pks = pk_map.get(table, [])
                schema_info += f"-- Table: {table}\n"
                schema_info += f"CREATE TABLE {table} (\n"
                schema_info += ",\n".join(columns)
                if pks:
                    schema_info += f",\n  PRIMARY KEY ({', '.join(pks)})"
                schema_info += "\n);\n\n"
                
                # Relationships for this table
                fks = fks_map.get(table, [])
                if fks:
                    schema_info += "Relationships:\n"
                    for col, ft, fc in fks:
                        schema_info += f"  - {table}.{col} -> {ft}.{fc}\n"
                    schema_info += "\n"
                else:
                    schema_info += "Relationships:\n  - None\n\n"

                # Sample data
                try:
                    cursor.execute(f'SELECT * FROM "{table}" LIMIT 3')
                    sample_rows = cursor.fetchall()
                    if sample_rows:
                        schema_info += f"/*\nSample data from {table}:\n"
                        if cursor.description:
                            headers = [desc[0] for desc in cursor.description]
                            schema_info += "\t".join(headers) + "\n"
                        for row in sample_rows:
                            schema_info += "\t".join(str(val) for val in row) + "\n"
                        schema_info += "*/\n\n"
                except Exception:
                    pass
            
            postgres_conn.commit()
            return schema_info
        except Exception as e:
            postgres_conn.rollback()
            raise e
        finally:
            cursor.close()
        
    except Exception as e:
        return f"Error getting database schema: {str(e)}"

    except Exception as e:
        return f"Error getting table relationships: {str(e)}"


@mcp.tool
async def execute_sql(sql_query: str) -> str:
    """
    Execute a SQL query against the database. Returns the result.
    Only SELECT queries are allowed; any DDL/DML will be rejected.
    """
    try:
        if postgres_conn is None:
            return "Database not connected. Please connect first."
        
        # Sanitize incoming text (strip markdown code fences)
        def _sanitize(s: str) -> str:
            s = (s or "").strip()
            s = re.sub(r"^```\s*sql\s*", "", s, flags=re.IGNORECASE)
            s = re.sub(r"^```", "", s)
            s = re.sub(r"```$", "", s)
            return s.strip()

        raw = _sanitize(sql_query)
        upper = raw.upper()
        # Allow SELECT and CTEs (WITH ... SELECT)
        if not (upper.startswith("SELECT") or upper.startswith("WITH")):
            return "Error: Only SELECT queries (including WITH ... SELECT) are allowed."

        cursor = postgres_conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute(raw)
            # If there is a result set
            if cursor.description:
                rows = cursor.fetchall()
                # Build plain-text table output
                headers = [desc.name if hasattr(desc, 'name') else desc[0] for desc in cursor.description]
                lines = []
                lines.append(f"SQL Query: {sql_query}")
                lines.append("")
                lines.append("\t".join(str(h) for h in headers))
                for row in rows:
                    record = []
                    for h in headers:
                        val = dict(row).get(h)
                        if hasattr(val, "isoformat"):
                            val = val.isoformat()
                        record.append(str(val))
                    lines.append("\t".join(record))
                postgres_conn.commit()
                return "\n".join(lines)
            else:
                postgres_conn.commit()
                return f"SQL Query: {sql_query}\n\nQuery executed successfully (no rows returned)"
        except Exception as e:
            postgres_conn.rollback()
            return f"Error executing SQL query: {str(e)}"
        finally:
            cursor.close()
    except Exception as e:
        return f"Error executing SQL query: {str(e)}"



# @mcp.tool
# async def check_sql(sql_query: str) -> str:
#     """
#     Validate a SQL string before execution.
#     - Ensures SELECT-only (blocks DDL/DML keywords)
#     - Checks referenced tables exist in public schema
#     - Hints for quoting reserved identifiers
#     Returns a readable report; does not execute the query.
#     """
#     try:
#         if postgres_conn is None:
#             return "Database not connected. Please connect first."
        
#         report_lines = []
#         # Sanitize incoming text (strip markdown code fences)
#         def _sanitize(s: str) -> str:
#             s = (s or "").strip()
#             s = re.sub(r"^```\s*sql\s*", "", s, flags=re.IGNORECASE)
#             s = re.sub(r"^```", "", s)
#             s = re.sub(r"```$", "", s)
#             return s.strip()

#         raw = _sanitize(sql_query)
#         if not raw:
#             return "Error: Empty query."

#         upper = raw.upper()
#         # Allow SELECT and CTEs (WITH ... SELECT)
#         if not (upper.startswith("SELECT") or upper.startswith("WITH")):
#             return "Blocked: Only SELECT queries (including WITH ... SELECT) are allowed."

#         # Block dangerous keywords anywhere in the query
#         if re.search(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|EXEC|EXECUTE|CALL)\b", upper):
#             return "Blocked: Disallowed SQL keyword detected. Only SELECT is permitted."

#         # Extract table-like identifiers from FROM and JOIN clauses (supports quoted and schema-qualified)
#         table_candidates = set()
#         for pattern in [
#             r"\bFROM\s+(\"?[A-Za-z_][\w]*\"?(?:\.\"?[A-Za-z_][\w]*\"?)?)",
#             r"\bJOIN\s+(\"?[A-Za-z_][\w]*\"?(?:\.\"?[A-Za-z_][\w]*\"?)?)",
#         ]:
#             for m in re.finditer(pattern, raw, flags=re.IGNORECASE):
#                 ident = m.group(1).strip()
#                 # Remove alias if provided as schema.table alias
#                 ident = ident.split()[0]
#                 # Strip trailing punctuation
#                 ident = ident.rstrip(",)")
#                 # If quoted, keep as-is; else lower-case for lookup
#                 if ident.startswith('"') and ident.endswith('"'):
#                     clean = ident.strip('"')
#                 else:
#                     # If schema qualified, take last part
#                     clean = ident.split('.')[-1]
#                 if clean:
#                     table_candidates.add(clean)

#         cursor = postgres_conn.cursor()
#         try:
#             # Check existence in public schema
#             existing = set()
#             missing = set()
#             for name in sorted(table_candidates):
#                 cursor.execute(
#                     """
#                     SELECT 1
#                     FROM information_schema.tables
#                     WHERE table_schema = 'public' AND table_name = %s
#                     """,
#                     (name,)
#                 )
#                 if cursor.fetchone():
#                     existing.add(name)
#                 else:
#                     missing.add(name)

#             report_lines.append("Check: SELECT-only ✓")
#             report_lines.append("Tables referenced: " + (", ".join(sorted(table_candidates)) if table_candidates else "<none detected>"))
#             report_lines.append("Tables found: " + (", ".join(sorted(existing)) if existing else "<none>"))
#             report_lines.append("Tables missing: " + (", ".join(sorted(missing)) if missing else "<none>"))

#             # Hint for reserved words
#             reserved = {"user", "order", "group", "select", "from"}
#             need_quotes = sorted(t for t in existing if t.lower() in reserved)
#             if need_quotes:
#                 report_lines.append("Hint: Quote reserved table names like \"" + "\", \"".join(need_quotes) + "\".")

#             status = "OK to execute" if not missing else "May fail: missing tables"
#             report_lines.append(f"Status: {status}")

#             return "\n".join(report_lines)
#         finally:
#             cursor.close()
#     except Exception as e:
#         return f"Error checking SQL: {str(e)}"

@mcp.tool
async def get_ocean_region_boundaries() -> str:
    """
    Returns approximate latitude/longitude boundaries for major ocean regions.
    Useful for constraining queries to specific ocean basins.
    """
    ocean_boundaries = {
        "Indian Ocean": {"lat_min": -30, "lat_max": 30, "lon_min": 20, "lon_max": 120},
        "Atlantic Ocean": {"lat_min": -60, "lat_max": 65, "lon_min": -70, "lon_max": 20},
        "Pacific Ocean": {"lat_min": -60, "lat_max": 65, "lon_min": 120, "lon_max": -70},
        "Southern Ocean": {"lat_min": -90, "lat_max": -60, "lon_min": -180, "lon_max": 180},
        "Arctic Ocean": {"lat_min": 65, "lat_max": 90, "lon_min": -180, "lon_max": 180}
    }
    return json.dumps(ocean_boundaries)
        

def main():
    """Main function to start the server."""
    # Connect to database
    connect_database()
    
    # Run the MCP server
    mcp.run()

if __name__ == "__main__":
    main()
