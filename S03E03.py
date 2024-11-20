import sys
import os
import logging
import argparse
import json
from openai import OpenAI
from text_classifier import text_chat
from aidev3_tasks import send_task
import requests  # Add this import
from tabulate import tabulate  # Add this import

DUMP_FOLDER = "S03E03-dump"  # Updated folder name
SCHEMA_FILE = "schema.json"
RESULTS_FILE = "results.json"

VERBOSE_VALUE = 15
logging.addLevelName(VERBOSE_VALUE, "VERBOSE")

def verbose(message, *args, **kws):
    logging.log(VERBOSE_VALUE, message, *args, **kws)
logging.verbose = verbose

# Set up argument parser
parser = argparse.ArgumentParser(description='AI Devs API script')
parser.add_argument('--debug', choices=['debug', 'info', 'verbose', 'off'], default='off', help='Debug mode')
parser.add_argument('--task', required=True, help='Task name')
parser.add_argument('--test', choices=['yes', 'no'], default='no', help='Test mode')
parser.add_argument('--start', type=int, choices=[0, 1, 2, 3], default=1,  # Updated to include 0
                    help='Start from step: 0-direct SQL, 1-retrieve schema, 2-TBD, 3-TBD')
parser.add_argument('--sql', type=str, help='SQL query to execute directly')  # New argument
parser.add_argument('--question', type=str, help='Natural language question to query the database')
args = parser.parse_args()

# Set up logging based on debug mode
if args.debug == "debug":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
elif args.debug == "info":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
elif args.debug == "verbose":
    logging.basicConfig(level=VERBOSE_VALUE, format='%(asctime)s - %(levelname)s - %(message)s')
else:
    logging.disable(sys.maxsize)

# API Keys setup
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
KEYDEVS = os.environ.get('AIDEVS')
if not KEYDEVS:
    raise ValueError("AIDEVS API KEY cannot be empty, setup environment variable AIDEVS")
if not OPENAI_API_KEY:
    raise ValueError("Open AI API key cannot be empty, setup environment variable OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# Add new constants for the SQL API
SQL_API_ENDPOINT = "https://centrala.ag3nts.org/apidb"
SQL_PROMPT = """
Analyze the provided database schema and generate an SQL query to answer the following question:
{question}

Available tables and their structure:
{schema}

Return only the SQL query without any additional text or formatting.
"""

def send_sql_query(query: str) -> dict:
    """Send SQL query to the API endpoint and return the response"""
    payload = {
        "task": "database",
        "apikey": KEYDEVS,
        "query": query
    }
    
    try:
        response = requests.post(SQL_API_ENDPOINT, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending SQL query: {e}")
        raise

def check_api_error(response: dict, context: str = "API call") -> None:
    """
    Check if the API response contains an error.
    Args:
        response: The API response dictionary
        context: Description of the operation being performed (for error messages)
    Raises:
        Exception: If error field is not "OK"
    """
    if not isinstance(response, dict):
        raise Exception(f"{context}: Invalid response format - expected dictionary, got {type(response)}")
    
    error = response.get('error')
    if error != 'OK':
        raise Exception(f"{context} failed with error: {error}")

def save_json_to_file(data: dict, dump_folder: str, filename: str, context: str = "Data") -> None:
    """
    Save dictionary data to a JSON file.
    Args:
        data: Dictionary containing data to save
        dump_folder: Folder to save the file
        filename: Name of the output file
        context: Description of the data being saved (for logging)
    """
    os.makedirs(dump_folder, exist_ok=True)
    file_path = os.path.join(dump_folder, filename)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    logging.info(f"{context} saved to {file_path}")

def generate_sql_query(question: str, schema: dict) -> str:
    """
    Generate SQL query using GPT-4 based on the question and schema.
    Args:
        question: Natural language question
        schema: Database schema dictionary
    Returns:
        Generated SQL query
    """
    # Format schema for prompt
    schema_str = json.dumps(schema, indent=2)
    
    messages = [
        {"role": "system", "content": """You are a SQL expert. Your task is to:
1. Analyze the provided database schema
2. Generate a precise SQL query that answers the given question
3. Return ONLY the SQL query without any explanations or markdown"""},
        {"role": "user", "content": f"""Database schema:
{schema_str}

Question: {question}

Generate SQL query to answer this question.
Output only the SQL query, do not use formatting ```sql```
"""}
    ]
    
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=messages,
            temperature=0.1,
            max_tokens=500
        )
        
        sql_query = response.choices[0].message.content.strip()
        logging.info(f"Generated SQL query: {sql_query}")
        return sql_query
        
    except Exception as e:
        logging.error(f"Error generating SQL query: {e}")
        raise

def process_natural_language_query(question: str, schema: dict) -> dict:
    """
    Process natural language query and return results.
    Args:
        question: Natural language question
        schema: Database schema dictionary
    Returns:
        Query results
    """
    try:
        # Generate SQL query
        sql_query = generate_sql_query(question, schema)
        logging.info(f"Executing SQL query: {sql_query}")
        
        # Execute the query
        result = send_sql_query(sql_query)
        check_api_error(result, f"Executing generated query: {sql_query}")
        
        return result
        
    except Exception as e:
        logging.error(f"Error processing natural language query: {e}")
        raise

def format_query_results(results: dict) -> None:
    """
    Format and display query results as a table.
    Args:
        results: Dictionary containing query results
    """
    if not results or 'reply' not in results:
        logging.error("No results to display")
        return
        
    try:
        # Extract just the values from each result row
        rows = []
        if results['reply']:
            # Get all unique keys from the results
            keys = list(results['reply'][0].keys())
            # Create rows with just the values
            for row in results['reply']:
                rows.append([row[key] for key in keys])
            
            # Create table with headers
            print("\nResults Table:")
            print(tabulate(rows, headers=keys, tablefmt='grid'))
            
            # Also print raw values
            print("\nValues only:")
            for row in rows:
                print(", ".join(str(value) for value in row))
            
    except Exception as e:
        logging.error(f"Error formatting results: {e}")

def load_schema(dump_folder: str) -> dict:
    """Load schema from the saved JSON file"""
    schema_path = os.path.join(dump_folder, SCHEMA_FILE)
    with open(schema_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_answer_list(results: dict) -> list:
    """Create a list of values from query results"""
    if not results or 'reply' not in results:
        raise ValueError("No results to process")
        
    # Extract first value from each row
    answer_list = []
    for row in results['reply']:
        # Get the first value from each row's values
        first_value = list(row.values())[0]
        answer_list.append(first_value)
    
    return answer_list

def main():
    schema = None
    
    # Step 0: Direct SQL query testing
    if args.start == 0:
        if not args.sql:
            logging.error("SQL query is required when using --start 0")
            return
            
        logging.info(f"Executing SQL query: {args.sql}")
        try:
            result = send_sql_query(args.sql)
            check_api_error(result, f"SQL query: {args.sql}")
            print("\nSQL Query Result:")
            print(json.dumps(result, indent=2))
            return
        except Exception as e:
            logging.error(f"Error executing SQL query: {e}")
            return

    # Step 1: Get database schema
    if args.start <= 1:
        logging.info("Starting from Step 1: Retrieving database schema")
        try:
            # Get list of tables
            tables_response = send_sql_query("show tables")
            check_api_error(tables_response, "Getting tables list")
            
            # Extract table names from the nested structure
            tables = [table['Tables_in_banan'] for table in tables_response['reply']]
            logging.debug(f"Found tables: {tables}")
            
            # Get structure for each table
            schema = {}
            for table in tables:
                table_structure = send_sql_query(f"desc {table}")
                check_api_error(table_structure, f"Getting structure for table {table}")
                
                # Create a more readable structure with field details
                fields = {}
                for field in table_structure['reply']:
                    fields[field['Field']] = {
                        'type': field['Type'],
                        'nullable': field['Null'],
                        'key': field['Key'],
                        'default': field['Default'],
                        'extra': field['Extra']
                    }
                schema[table] = fields
                
                logging.debug(f"Structure for {table}:")
                logging.debug(json.dumps(fields, indent=2))
            
            # Save schema
            save_json_to_file(schema, DUMP_FOLDER, SCHEMA_FILE, "Schema")
                
        except Exception as e:
            logging.error(f"Error in Step 1: {e}")
            return
    else:
        # Load schema from file if starting from step 2 or later
        try:
            schema = load_schema(DUMP_FOLDER)
        except Exception as e:
            logging.error(f"Error loading schema: {e}")
            return

    # Step 2: Process natural language query
    if args.start <= 2 and schema:
        logging.info("Starting Step 2: Natural Language Query Processing")
        try:
            if not args.question:
                logging.error("Question is required for natural language processing")
                return
                
            result = process_natural_language_query(args.question, schema)
            print("\nQuery Result:")
            print(json.dumps(result, indent=2))
            
            # Save results
            save_json_to_file(result, DUMP_FOLDER, RESULTS_FILE, "Query results")
            
        except Exception as e:
            logging.error(f"Error in Step 2: {e}")
            return

    # Step 3: Format and display results
    if args.start <= 3:
        logging.info("Starting Step 3: Results Formatting")
        try:
            # Load results from file
            results_path = os.path.join(DUMP_FOLDER, RESULTS_FILE)
            if not os.path.exists(results_path):
                logging.error("No results file found. Run step 2 first.")
                return
                
            with open(results_path, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            format_query_results(results)
            
            # Create answer list and send to server
            answer_list = create_answer_list(results)
            response = send_task(args.task, KEYDEVS, answer_list)
            
            if response:
                if response.get('code') == 0:
                    print("Task completed successfully!")
                    print("Server response: %s", response.get('message', 'No message provided'))
                else:
                    logging.error("Task failed with error: %s", response.get('message', 'Unknown error'))
            else:
                logging.error("Failed to get response from server")
                
        except FileNotFoundError as e:
            logging.error(f"Required file not found: {e}. Please run from earlier step first.")
            return
        except Exception as e:
            logging.error(f"Error in Step 3: {e}")
            return

if __name__ == "__main__":
    main() 