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
from llm_config import get_llm_config

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

def extract_sql_from_message(content):
    """Extract SQL query from a message content using multiple patterns."""
    # Pattern 1: Look for SQL between triple backticks
    sql_match = re.search(r'```sql\n(.*?)\n```', content, re.DOTALL)
    if sql_match:
        return sql_match.group(1).strip()
    
    # Pattern 2: Look for SQL between single backticks
    sql_match = re.search(r'`(SELECT.*?)`', content, re.DOTALL)
    if sql_match:
        return sql_match.group(1).strip()
    
    # Pattern 3: Look for SQL starting with SELECT
    sql_match = re.search(r'(SELECT.*?)(?:;|$)', content, re.IGNORECASE | re.DOTALL)
    if sql_match:
        return sql_match.group(1).strip()
    
    return None

def process_question(question_data, llm_config):
    """Process a single question through the agent pipeline."""
    # Load the corresponding schema using db_id
    full_schema = load_schema(question_data['db_id'])
    
    # Extract relevant schema parts
    schema = extract_relevant_schema(full_schema, question_data['question'])
    
    # Create user proxy
    user_proxy = UserProxyAgent(
        name="User",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=0,
        llm_config=llm_config
    )
    
    # Create agents with more focused system messages
    question_analyzer = QuestionAnalyzer(llm_config)
    sql_generator = SQLGenerator(llm_config)
    query_validator = QueryValidator(llm_config)
    
    # Create group chat with shorter max_round
    groupchat = GroupChat(
        agents=[user_proxy, question_analyzer, sql_generator, query_validator],
        messages=[],
        max_round=5,  # Reduced from 10 to 5
        speaker_selection_method="round_robin",
        allow_repeat_speaker=False
    )
    
    # Create group chat manager
    manager = GroupChatManager(
        groupchat=groupchat,
        llm_config=llm_config
    )
    
    # Prepare the question with minimal context, without showing the gold SQL
    question = f"""Question: {question_data['question']}

Schema:
{schema}

Please analyze the question and generate a valid SQL query."""
    
    # Start the conversation
    chat_result = user_proxy.initiate_chat(
        manager,
        message=question
    )
    
    # Extract the final SQL query from the conversation
    final_query = None
    for message in reversed(chat_result.chat_history):
        # Check both assistant and user messages
        if message['role'] in ['assistant', 'user']:
            sql = extract_sql_from_message(message['content'])
            if sql:
                final_query = sql
                break
    
    # Compare the generated query with the gold SQL
    if final_query:
        normalized_gold = normalize_sql(question_data['gold_sql'])
        normalized_generated = normalize_sql(final_query)
        is_match = normalized_gold == normalized_generated
        
        # Log only the essential comparison information
        logger.info(f"Question {question_data['question_id']}:")
        logger.info(f"Normalized Gold: {normalized_gold}")
        logger.info(f"Normalized Generated: {normalized_generated}")
        logger.info(f"Match: {'CORRECT' if is_match else 'INCORRECT'}")
        logger.info("-" * 80)
        
        return is_match
    else:
        logger.info(f"Question {question_data['question_id']}: NO SQL GENERATED")
        logger.info("-" * 80)
        return False

def main():
    # Get LLM configuration
    llm_config = get_llm_config()
    
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
            is_match = process_question(question_data, llm_config)
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