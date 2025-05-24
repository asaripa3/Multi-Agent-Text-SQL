"""
Query Validator agent that validates and optimizes SQL queries.
"""
from autogen import AssistantAgent
import json

class QueryValidator(AssistantAgent):
    def __init__(self, llm_config):
        system_message = """You are a SQL query validator. Your task is to:
1. Read the generated SQL query
2. Validate:
   - Syntax correctness
   - Table and column existence
   - Join conditions
   - WHERE clause logic
3. Optimize the query if needed
4. Provide feedback in a structured format

Example output format:
{
    "is_valid": true,
    "optimizations": [
        "Added index hint for better performance",
        "Simplified WHERE clause"
    ],
    "suggestions": [
        "Consider adding a LIMIT clause",
        "Add more specific conditions"
    ],
    "final_query": "SELECT ..."
}"""
        
        super().__init__(
            name="QueryValidator",
            system_message=system_message,
            llm_config=llm_config
        )

    def run(self, state: dict) -> dict:
        sql_query = state.get("sql_query")
        schema = state.get("schema", "")

        if not sql_query:
            raise ValueError("Missing 'sql_query' in state")

        prompt = f"""You are given the following SQL query and the corresponding PostgreSQL schema. Validate the SQL query for syntax, correctness, and logical consistency with the schema. Provide structured feedback as shown in the expected format.

SQL Query:
```sql
{sql_query}
```

Database Schema:
```sql
{schema}
```

Respond in the following JSON format:
{{
    "is_valid": true,
    "optimizations": [],
    "suggestions": [],
    "final_query": "..."
}}
"""

        response = self.generate_reply(messages=[{"role": "user", "content": prompt}])
        try:
            result = response if isinstance(response, dict) else json.loads(response)
        except Exception as e:
            raise ValueError(f"Failed to parse validation result as JSON: {e}")

        return {
            "validation_result": result,
            "final_query": result.get("final_query")
        }