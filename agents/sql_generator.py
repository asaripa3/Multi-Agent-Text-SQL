"""
SQL Generator agent that creates SQL queries based on the analysis.
"""
from autogen import AssistantAgent

class SQLGenerator(AssistantAgent):
    def __init__(self, llm_config):
        system_message = """You are a SQL query generator. Your task is to:
1. Read the analysis from QuestionAnalyzer
2. Generate a MySQL query that:
   - Uses the identified tables and columns
   - Implements the required relationships
   - Applies the necessary conditions
   - Follows MySQL syntax
3. Provide the query with comments explaining each part
4. Do not execute the query

Example output format:
-- Query to find [purpose]
SELECT 
    t1.col1,  -- [explanation]
    t2.col2   -- [explanation]
FROM 
    table1 t1
    JOIN table2 t2 ON t1.id = t2.id  -- [explanation]
WHERE 
    t1.col1 > 0  -- [explanation]
    AND t2.col2 = 'value';  -- [explanation]"""
        
        super().__init__(
            name="SQLGenerator",
            system_message=system_message,
            llm_config=llm_config
        ) 