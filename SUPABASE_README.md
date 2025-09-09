# Supabase MCP Server

This is a Model Context Protocol (MCP) server for querying Supabase PostgreSQL databases using natural language.

## Features

- **Secure Query Execution**: Only SELECT queries are allowed for security
- **Database Schema Analysis**: Get complete database schema information
- **Table Relationships**: Analyze foreign key relationships between tables
- **Natural Language Interface**: Query your database using conversational language
- **Real-time Data Access**: Direct connection to your Supabase database

## Setup

### 1. Install Dependencies

```bash
pip install -r requirement.txt
```

### 2. Configure Database Connection

Edit `supabaseserver.py` and update the connection string:

```python
SUPABASE_CONNECTION_STRING = "postgresql://postgres:[YOUR-PASSWORD]@db.hbfmvzzjbvqzmwpxnrcb.supabase.co:5432/postgres"
```

Replace `[YOUR-PASSWORD]` with your actual Supabase database password.

### 3. Run the Server

```bash
python supabaseserver.py
```

### 4. Run the Client

```bash
python mcpclient.py
```

**Note**: The client now supports both SQLite/Turso and Supabase servers. Tools will be prefixed with server names (e.g., `sqlassistant_execute_sql`, `supabaseassistant_execute_sql`).

## Available Tools

### 1. `execute_sql`
Execute SELECT queries on your Supabase database.

**Input**: SQL query string (SELECT only)
**Example**: `"SELECT * FROM users WHERE age > 25"`

### 2. `get_database_schema`
Get complete database schema including all tables, columns, and sample data.

**Input**: None required
**Returns**: Full database schema with CREATE TABLE statements

### 3. `get_table_names`
Get list of all table names in the database.

**Input**: None required
**Returns**: Comma-separated list of table names

### 4. `get_table_relationships`
Analyze foreign key relationships between tables.

**Input**: None required
**Returns**: Detailed relationship information

### 5. `describe_table`
Get detailed information about a specific table.

**Input**: Table name (string)
**Example**: `"users"`

## Security Features

- **SELECT-Only Queries**: Only SELECT statements are allowed
- **Dangerous Keyword Blocking**: Prevents DROP, DELETE, INSERT, UPDATE, etc.
- **Schema Protection**: No structural changes allowed
- **Clear Error Messages**: Informative feedback for blocked operations

## Example Usage

```
You: What tables are in my Supabase database?
Assistant: [Uses supabaseassistant_get_table_names]

You: Show me all users with their email addresses from Supabase
Assistant: [Uses supabaseassistant_execute_sql: SELECT email FROM users]

You: How are the users and orders tables connected in Supabase?
Assistant: [Uses supabaseassistant_get_table_relationships]

You: What tables are in my Turso database?
Assistant: [Uses sqlassistant_get_table_names]
```

## Differences from SQLite/Turso Server

- Uses PostgreSQL-specific SQL syntax
- Connects directly to Supabase (no local sync needed)
- Uses `information_schema` for metadata queries
- Supports PostgreSQL data types and features
- Uses `psycopg2` for database connectivity

## Troubleshooting

### Connection Issues
- Verify your Supabase connection string
- Check if your IP is whitelisted in Supabase
- Ensure the database password is correct

### Query Errors
- Remember: Only SELECT queries are allowed
- Check table and column names are correct
- Use PostgreSQL syntax (not SQLite)

## Requirements

- Python 3.8+
- Supabase PostgreSQL database
- Valid Supabase connection string
- Required packages: `fastmcp`, `psycopg2-binary`, `langchain`, etc.
