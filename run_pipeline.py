def extract_json_block(text):
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not match:
        raise ValueError("Could not extract JSON block from validation content.")
    return json.loads(match.group(1))
"""
Main script for running the SQL multi-agent pipeline.
"""
import json
import re
import logging
from datetime import datetime
from autogen import UserProxyAgent, GroupChat, GroupChatManager
from agents.question_analyzer import QuestionAnalyzer
from agents.sql_generator import SQLGenerator
from agents.query_validator import QueryValidator
from llm_config import get_llm_config, get_sqlcoder_config
from planning.agent_step import AgentStep
from planning.planner import Planner
from agents.fallback_sql_generator import FallbackSQLGenerator
from control.validator_hooks import should_run_fallback, inject_fallback_step
from state.shared_state import reset_state, update_state, get_state, get_full_state, get_state_reference

# Set up logging
# Create a custom logger
logger = logging.getLogger('sql_validator')
logger.setLevel(logging.INFO)

# Create a file handler
file_handler = logging.FileHandler(f'sql_validation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
file_handler.setLevel(logging.INFO)

# Create a formatter
formatter = logging.Formatter('%(message)s')
file_handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(file_handler)

# Disable logging for other modules
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('autogen').setLevel(logging.WARNING)

def normalize_sql(sql):
    """Normalize SQL query for comparison by removing extra spaces, quotes, and case."""
    # Remove extra whitespace
    sql = re.sub(r'\s+', ' ', sql)
    # Remove quotes
    sql = sql.replace('"', '').replace("'", '')
    # Convert to lowercase
    sql = sql.lower()
    # Remove trailing semicolons
    sql = sql.rstrip(';')
    return sql.strip()

def extract_relevant_schema(schema_text, question):
    """Extract only the relevant tables and their relationships based on the question."""
    # Split schema into individual CREATE TABLE statements
    tables = schema_text.split('CREATE TABLE')
    relevant_tables = []
    
    # Simple keyword matching to find relevant tables
    keywords = question.lower().split()
    for table in tables:
        if any(keyword in table.lower() for keyword in keywords):
            # Only keep the table name and column definitions
            table_lines = table.split('\n')
            filtered_lines = [line for line in table_lines if 'CREATE TABLE' in line or 'PRIMARY KEY' in line or 'FOREIGN KEY' in line]
            if filtered_lines:
                relevant_tables.append('CREATE TABLE' + '\n'.join(filtered_lines))
    
    return '\n'.join(relevant_tables) if relevant_tables else schema_text[:1000]  # Fallback to first 1000 chars

def load_schema(db_id):
    """Load the database schema for a specific database ID."""
    with open('data_minidev/MINIDEV/dev_tables.json', 'r') as f:
        schema_data = json.load(f)
        # Find the schema for the given db_id
        db_schema = next((db for db in schema_data if db['db_id'] == db_id), None)
        if not db_schema:
            raise ValueError(f"Schema not found for database ID: {db_id}")
        
        # Convert JSON schema to SQL CREATE TABLE statements
        create_statements = []
        
        # Create a mapping of table indices to table names
        table_names = db_schema['table_names']
        
        # Group columns by table
        table_columns = {}
        for col_info, col_name, col_type in zip(
            db_schema['column_names_original'],
            db_schema['column_names'],
            db_schema['column_types']
        ):
            table_idx = col_info[0]
            if table_idx == -1:  # Skip the * column
                continue
            if table_idx not in table_columns:
                table_columns[table_idx] = []
            table_columns[table_idx].append((col_name[1], col_type))
        
        # Generate CREATE TABLE statements
        for table_idx, columns in table_columns.items():
            table_name = table_names[table_idx]
            column_defs = []
            
            for col_name, col_type in columns:
                # Convert column type to SQL type
                sql_type = col_type.upper()
                if sql_type == 'TEXT':
                    sql_type = 'VARCHAR(255)'
                elif sql_type == 'INTEGER':
                    sql_type = 'INT'
                
                column_defs.append("`{}` {}".format(col_name, sql_type))
            
            # Use string formatting for the CREATE TABLE statement
            create_stmt = "CREATE TABLE `{}` (\n    {}\n)".format(
                table_name,
                ',\n    '.join(column_defs)
            )
            create_statements.append(create_stmt)
        
        return '\n\n'.join(create_statements)

def load_questions():
    """Load all questions from the dataset."""
    with open('data_minidev/MINIDEV/mini_dev_mysql.json', 'r') as f:
        questions = json.load(f)
        return [{
            'question_id': i,  # Add question ID
            'question': q['question'],
            'evidence': q['evidence'],
            'gold_sql': q['SQL'],
            'difficulty': q['difficulty'],
            'db_id': q['db_id']
        } for i, q in enumerate(questions, 1)]

import re

def extract_sql_from_message(content: str) -> str:
    # Try to match ```sql ... ``` first
    match = re.search(r"```sql\s*(.*?)```", content, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try plain triple backticks
    match = re.search(r"```\s*(.*?)```", content, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try SELECT-fallback pattern
    match = re.search(r"(SELECT .*?);", content, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return None

def validate_sql_with_agent(query: str, schema: str, llm_config: dict) -> dict:
    validator = QueryValidator(llm_config)
    prompt = f"""You are given a SQL query and schema. Validate the query.
SQL Query:
```sql
{query}
```

Schema:
```sql
{schema}
```

Respond in JSON:
{{
  "is_valid": true,
  "final_query": "...",
  "suggestions": []
}}"""
    response = validator.generate_reply(messages=[{"role": "user", "content": prompt}])
    raw = response if isinstance(response, str) else json.dumps(response)
    cleaned = re.sub(r"```json|```", "", raw).strip()
    return json.loads(cleaned)

def run_fallback_phase(schema, analysis, validation_result, sql_config, llm_config):
    logger.warning("⚠️ Running fallback due to validation failure...")
    fallback_agent = FallbackSQLGenerator(sql_config)
    fallback_state = {
        "schema": schema,
        "analysis": analysis,
        "validation_result": validation_result
    }
    result = fallback_agent.run(fallback_state)
    fallback_query = result.get("final_query")

    if not fallback_query:
        logger.error("❌ Fallback failed to generate a valid SQL.")
        return None

    validation = validate_sql_with_agent(fallback_query, schema, llm_config)
    if validation.get("is_valid"):
        logger.info("✅ Fallback query validated successfully.")
        return validation.get("final_query")
    else:
        logger.error("❌ Fallback query also failed validation.")
        return None

def process_question(question_data, llm_config, sql_config):
    reset_state()
    full_schema = load_schema(question_data["db_id"])
    schema = extract_relevant_schema(full_schema, question_data["question"])

    update_state("question", question_data["question"])
    update_state("schema", schema)

    steps = [
        AgentStep("QuestionAnalysis", QuestionAnalyzer(llm_config), ["question", "schema"], ["analysis"]),
        AgentStep("SQLGeneration", SQLGenerator(sql_config), ["question", "schema", "analysis"], ["sql_query"]),
        AgentStep("QueryValidation", QueryValidator(llm_config), ["sql_query", "schema"], ["validation_result"])
    ]

    planner = Planner(steps)
    planner.run(get_state_reference())

    analysis = get_state("analysis")
    sql_query = get_state("sql_query")
    validation_result = get_state("validation_result")
    final_query = get_state("final_query")

    # Parse validation result
    final_query = None
    try:
        parsed = extract_json_block(validation_result.get("content", ""))

        if parsed.get("is_valid"):
            final_query = parsed.get("final_query") or sql_query
        else:
            final_query = run_fallback_phase(schema, analysis, parsed, sql_config, llm_config)
    except Exception as e:
        pass

    # Compare the generated query with the gold SQL
    if final_query:
        normalized_gold = normalize_sql(question_data['gold_sql'])
        normalized_generated = normalize_sql(final_query)
        is_match = normalized_gold == normalized_generated

        logger.info(f"Normalized Gold: {normalized_gold}")
        logger.info(f"Normalized Generated: {normalized_generated}")
        logger.info(f"Match: {'CORRECT' if is_match else 'INCORRECT'}")

        return is_match
    else:
        return False

def main():
    # Get LLM configuration
    llm_config = get_llm_config()
    sql_config = get_sqlcoder_config()
    
    # Load all questions
    questions = load_questions()
    
    # Track statistics
    total_questions = len(questions)
    correct_matches = 0
    
    # Process each question sequentially
    for i, question_data in enumerate(questions, 1):
        print(f"\nProcessing question {i} of {total_questions}")
        print(f"Question: {question_data['question']}")
        print(f"Database: {question_data['db_id']}")
        print("-" * 80)
        
        try:
            is_match = process_question(question_data, llm_config, sql_config)
            if is_match:
                correct_matches += 1
        except Exception as e:
            logger.info(f"Question {question_data['question_id']}: ERROR - {str(e)}")
            logger.info("-" * 80)
            continue
    
    # Log final statistics
    accuracy = (correct_matches / total_questions) * 100
    logger.info(f"\nFinal Statistics:")
    logger.info(f"Total Questions: {total_questions}")
    logger.info(f"Correct Matches: {correct_matches}")
    logger.info(f"Accuracy: {accuracy:.2f}%")

if __name__ == "__main__":
    main()