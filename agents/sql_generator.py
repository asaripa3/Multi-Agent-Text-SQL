"""
SQL Generator agent that creates SQL queries based on the analysis.
"""
from autogen import AssistantAgent
import json
import re

class SQLGenerator(AssistantAgent):
    def __init__(self, llm_config):
        system_message = """You are a SQL generation agent specialized in Postgres. Follow the instructions carefully and use table aliases."""
        
        super().__init__(
            name="SQLGenerator",
            system_message=system_message,
            llm_config=llm_config
        )

    def run(self, state: dict) -> dict:
        question = state.get("question")
        schema = state.get("schema")
        analysis = state.get("analysis")
        if not question or not schema or not analysis:
            raise ValueError("Missing one of: question, schema, or analysis in state")

        prompt = f"""### Instructions:
You are an expert Postgres SQL query writer. Your task is to convert a natural language question into a syntactically correct SQL query using a database schema.
Adhere to these rules:
- **Deliberately go through the question and database schema word by word** to appropriately answer the question.
- **Use Table Aliases** to prevent ambiguity. For example, `SELECT t1.col1, t2.col1 FROM t1 JOIN t2 ON t1.id = t2.id`.
- When creating a ratio, always cast the numerator as float.

### Input:
Generate a SQL query that answers the following natural language question:
\"\"\"{question}\"\"\"

This query will run on a PostgreSQL database. Below is the database schema and extracted analysis to help you:

### PostgreSQL Schema:
{schema}

### Analysis (relevant tables, columns, and key conditions):
{json.dumps(analysis, indent=2)}

### Response:
Based on your instructions, here is the SQL query I have generated to answer the question `{question}`:
```sql
"""
        response = self.generate_reply(messages=[{"role": "user", "content": prompt}])
        content = response["content"] if isinstance(response, dict) else str(response)

        # Extract SQL block from model output
        match = re.search(r"```sql\s*(.*?)```", content, re.DOTALL)
        if not match:
            match = re.search(r"```\s*(.*?)```", content, re.DOTALL)
        if not match:
            match = re.search(r"(SELECT .*?);", content, re.DOTALL | re.IGNORECASE)
        if not match:
            print("MODEL RESPONSE:\n", content)
            raise ValueError("Failed to extract SQL from response")

        return {"sql_query": match.group(1).strip()}