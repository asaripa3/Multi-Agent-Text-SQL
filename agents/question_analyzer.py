"""
Question analyzer agent that identifies required tables and columns from the question.
"""
from autogen import AssistantAgent

class QuestionAnalyzer(AssistantAgent):
    def __init__(self, llm_config):
        system_message = """You are a SQL question analyzer. Your task is to:
1. Read the question and the provided database schema
2. Identify:
   - Required tables
   - Required columns
   - Relationships between tables
   - Any conditions or filters needed
3. Provide a structured analysis in JSON format
4. Do not write any SQL queries

Example output format:
{
    "tables": ["table1", "table2"],
    "columns": {
        "table1": ["col1", "col2"],
        "table2": ["col3", "col4"]
    },
    "relationships": [
        {"from": "table1.col1", "to": "table2.col3"}
    ],
    "conditions": ["col1 > 0", "col3 = 'value'"]
}"""
        
        super().__init__(
            name="QuestionAnalyzer",
            system_message=system_message,
            llm_config=llm_config
        ) 