"""
Query Validator agent that validates and optimizes SQL queries.
"""
from autogen import AssistantAgent

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