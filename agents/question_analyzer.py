"""
Question analyzer agent that identifies required tables and columns from the question.
"""
from autogen import AssistantAgent
import json

class QuestionAnalyzer(AssistantAgent):
    def __init__(self, llm_config):
        system_message = """As an experienced and professional database administrator, your task is to analyze a user question and a database schema to provide relevant information. The database schema consists of table descriptions, each containing multiple column descriptions. Your goal is to identify the relevant tables and columns based on the user question and evidence provided.

[Instruction]
1. Discard any table schema that is not related to the user question and evidence.
2. Sort the columns in each relevant table in descending order of relevance and keep the top 6 columns.
3. Ensure that at least 3 tables are included in the final output JSON.
4. The output should be in JSON format.
5. Do not modify table names or column names from table_names_original and column_names_original at any point in the process.

Important: Never interchange or mix columns between different tables. Only use columns that belong to the specified table. Ensure the SQL query uses correct table-column relationships as defined in the schema.

[Requirements]
1. If a table has less than or equal to 10 columns, mark it as "keep_all".
2. If a table is completely irrelevant to the user question and evidence, mark it as "drop_all".
3. Prioritize the columns in each relevant table based on their relevance.

[Important Notes]
- The JSON should start and end with curly braces.
- Ensure that the key-value pairs are correctly formatted with no extra characters or text.
- If a table is relevant, use "keep_all", and if it's irrelevant, use "drop_all".
- For the relevant tables, list the columns in an array, and only include the top columns in descending order of relevance.
- The output should strictly follow the format without any extra text.

[Answer]
'''json
{
  "account": ["account_id", "district_id", "frequency", "date"],
  "client": ["client_id", "gender", "birth_date", "district_id"],
  "district": ["district_id", "A11", "A2", "A4", "A6", "A7"]
}
'''

==========
Here is a new example, please start answering:
User Question : {{user_question}}
Schema Details: {{DB_Json}}
evidence: {{evidence}}"""
        
        super().__init__(
            name="QuestionAnalyzer",
            system_message=system_message,
            llm_config=llm_config
        )

    def run(self, state: dict) -> dict:
        question = state.get("question")
        schema = state.get("schema")
        if not question or not schema:
            raise ValueError("Missing 'question' or 'schema' in state")

        prompt = f"""Given the following SQL database schema and a natural language question, analyze the question and extract relevant tables, columns, relationships, and conditions.

Schema:
{schema}

Question:
{question}

Respond in the structured JSON format as previously instructed.
"""
        response = self.generate_reply(messages=[{"role": "user", "content": prompt}])
        print("\n=== RAW MODEL RESPONSE ===")
        print(response)
        print("==========================")
        import re

        try:
            content = response["content"] if isinstance(response, dict) else response

            # Extract JSON block inside ```json ... ```
            match = re.search(r"```json\s*(.*?)```", content, re.DOTALL)
            json_str = match.group(1) if match else content

            analysis = json.loads(json_str)
            print("=== PARSED ANALYSIS ===")
            print(json.dumps(analysis, indent=2))
        except Exception as e:
            print("=== ERROR DURING ANALYSIS ===")
            print(e)
            raise ValueError(f"Failed to parse analysis as JSON: {e}")

        return {"analysis": analysis}