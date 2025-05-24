from autogen import AssistantAgent
import json
import re

class FallbackSQLGenerator(AssistantAgent):
    def __init__(self, llm_config):
        system_message = """You are a fallback SQL query generator. Your task is to:
1. Read the previous analysis and failed SQL query feedback
2. Generate a corrected MySQL query that:
   - Resolves issues from the previous validation
   - Uses identified tables, columns, and conditions
3. Explain each part using inline comments
4. Respond only with the SQL query in triple backticks
"""
        super().__init__(
            name="FallbackSQLGenerator",
            system_message=system_message,
            llm_config=llm_config
        )

    def run(self, state: dict) -> dict:
        analysis = state.get("analysis")
        validation = state.get("validation_result")

        if not analysis or not validation or validation.get("is_valid", True):
            raise ValueError("Fallback requires failed validation and existing analysis.")

        prompt = f"""The previous SQL query was invalid. Use the following analysis and suggestions to regenerate a valid MySQL query.

Analysis:
{json.dumps(analysis, indent=2)}

Suggestions:
{json.dumps(validation.get("suggestions", []), indent=2)}

Respond with the new SQL query in triple backticks:
```sql
SELECT ...
```"""

        response = self.generate_reply(messages=[{"role": "user", "content": prompt}])
        content = response if isinstance(response, str) else json.dumps(response)

        match = re.search(r"```sql\n(.*?)\n```", content, re.DOTALL)
        if not match:
            raise ValueError("Failed to extract fallback SQL query.")
        
        new_sql = match.group(1).strip()

        # Reuse validator logic
        schema = state.get("schema", "")
        validator_prompt = f"""You are given a SQL query and the PostgreSQL schema. Validate the SQL query.

SQL Query:
```sql
{new_sql}
```

Schema:
```sql
{schema}
```

Respond in this format:
{{
  "is_valid": true,
  "final_query": "...",
  "suggestions": []
}}"""

        validation_response = self.generate_reply(messages=[{"role": "user", "content": validator_prompt}])
        try:
            parsed = json.loads(validation_response if isinstance(validation_response, str) else json.dumps(validation_response))
            if parsed.get("is_valid"):
                return {"final_query": parsed.get("final_query") or new_sql}
            else:
                raise ValueError(f"Fallback SQL validation failed: {parsed.get('suggestions')}")
        except Exception as e:
            raise ValueError(f"Failed to validate fallback SQL: {e}")
