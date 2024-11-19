import sys
import os
import logging
import argparse
import json
from openai import OpenAI
from text_classifier import text_chat
from aidev3_tasks import send_task

KEYWORDS_PROMPT = """
Generate a list of keywords (tags) that represent the essential aspects of the provided Polish text.

Rules:
Keywords must be in Polish.
Reduce each keyword to its base form (lemma).
Use single-word keywords only.
Always include proper names (e.g., first name and surname).
Exclude stop words such as "i", "w", "na", etc.

###Format
Be returned in a JSON format as a list of words, separated by commas: {"keywords": ["slowo1", "slowo2", ..., "slowoN"]}
Do not output any other formatting like ```json``` or other text.

###Input text (in Polish):
"""

DUMP_FOLDER = "S03E01-dump"

VERBOSE_VALUE = 15  # Choose a value between existing levels
logging.addLevelName(VERBOSE_VALUE, "VERBOSE")

def verbose(message, *args, **kws):
    logging.log(VERBOSE_VALUE, message, *args, **kws)
logging.verbose = verbose

# Set up argument parser
parser = argparse.ArgumentParser(description='AI Devs API script')
parser.add_argument('--debug', choices=['debug', 'info', 'verbose', 'off'], default='off', help='Debug mode')
parser.add_argument('--task', required=True, help='Task name')
parser.add_argument('--folder1', required=True, help='Path to the first folder containing files')
parser.add_argument('--folder2', required=True, help='Path to the second folder containing files')
parser.add_argument('--test', choices=['yes', 'no'], default='no', help='Test mode')
parser.add_argument('--start', type=int, choices=[1, 2, 3], default=1, 
                    help='Start from step: 1-processing folders, 2-TBD, 3-TBD')
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

# Data structures to hold files and their tags
fact_list = []    # Will hold files from folder1
input_list = []   # Will hold files from folder2
output_list = []  # Will hold joined files from fact_list and input_list

# Test configuration
test_include = [
    "2024-11-12_report-00-sektor_C4.txt",
    "f04.txt"
]

def ensure_dump_folder_exists():
    """Ensure the dump folder exists."""
    if not os.path.exists(DUMP_FOLDER):
        os.makedirs(DUMP_FOLDER)
        logging.info(f"Created '{DUMP_FOLDER}' directory.")
    return DUMP_FOLDER

def dump_results():
    """Dump the fact_list and input_list to files in human-readable format."""
    ensure_dump_folder_exists()
    
    # Dump fact_list
    fact_file = os.path.join(DUMP_FOLDER, 'fact_list.json')
    with open(fact_file, 'w', encoding='utf-8') as f:
        json.dump(fact_list, f, ensure_ascii=False, indent=2)
    logging.info(f"Dumped fact_list to {fact_file}")
    
    # Dump input_list
    input_file = os.path.join(DUMP_FOLDER, 'input_list.json')
    with open(input_file, 'w', encoding='utf-8') as f:
        json.dump(input_list, f, ensure_ascii=False, indent=2)
    logging.info(f"Dumped input_list to {input_file}")

def process_folder(folder_path, target_list):
    """
    Generic function to process a folder and populate a target list with files and their tags
    """
    for filename in os.listdir(folder_path):
        # Skip files not in test_include list when in test mode
        if args.test == 'yes' and filename not in test_include:
            logging.debug(f"Skipping {filename} - not in test include list")
            continue
            
        if filename.endswith('.txt'):
            # Read the file content
            with open(os.path.join(folder_path, filename), 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Get keywords from OpenAI
            response = text_chat(content, client, args, KEYWORDS_PROMPT)
            
            try:
                # Parse the JSON response
                keywords = json.loads(response)
                tags = keywords.get('keywords', [])
                
                # Sort tags with capital letters first, then lowercase
                tags.sort(key=lambda x: (not x[0].isupper(), x.lower()))
                
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse OpenAI response for {filename}: {e}")
                logging.error(f"Response: {response}")
                tags = []
            
            # Add to target list
            target_list.append({
                "filename": filename,
                "tags": tags
            })
            logging.debug(f"Processed {filename} with tags: {tags}")

def process_folders():
    # Process folder1 for facts
    logging.info(f"Processing folder1: {args.folder1}")
    process_folder(args.folder1, fact_list)
    
    # Process folder2 for inputs
    logging.info(f"Processing folder2: {args.folder2}")
    process_folder(args.folder2, input_list)
    
    logging.info(f"Processed {len(fact_list)} files in fact_list")
    logging.info(f"Processed {len(input_list)} files in input_list")

def join_keywords():
    """
    Create output_list based on keyword matches between input_list and fact_list.
    For each file in input_list, if any of its keywords match with any keywords
    in fact_list files, merge both keyword lists (removing duplicates).
    Adds two tags from filename:
    - date and report number (e.g., "2024-11-12 report-00")
    - sector (e.g., "sektor C4")
    """
    logging.info("Starting keyword joining process")
    
    # Create a flat list of all keywords from fact_list for faster lookup
    fact_keywords = {keyword: entry["tags"] 
                    for entry in fact_list 
                    for keyword in entry["tags"]}
    
    # Process each file in input_list
    for input_entry in input_list:
        output_entry = {
            "filename": input_entry["filename"],
            "tags": input_entry["tags"].copy()  # Start with input tags
        }
        
        # Check each keyword from input file
        for keyword in input_entry["tags"]:
            if keyword in fact_keywords:
                # If match found, merge keywords from both lists
                merged_tags = set(output_entry["tags"]) | set(fact_keywords[keyword])
                output_entry["tags"] = list(merged_tags)  # Convert back to list
                logging.debug(f"Match found for {input_entry['filename']} on keyword '{keyword}'")
        
        # Sort tags (capital letters first, then lowercase)
        output_entry["tags"].sort(key=lambda x: (not x[0].isupper(), x.lower()))
        
        # Process filename to create two additional tags
        filename_without_ext = os.path.splitext(input_entry["filename"])[0]  # Remove .txt
        parts = filename_without_ext.split('-sektor_')  # Split at -sektor_
        if len(parts) == 2:
            # First part: date and report number (replace _ with space)
            date_report = parts[0].replace('_', ' ')
            # Second part: sector (add "sektor" prefix)
            sector = f"sektor {parts[1]}"
            
            # Add both new tags if they're not already in the list
            if date_report not in output_entry["tags"]:
                output_entry["tags"].append(date_report)
            if sector not in output_entry["tags"]:
                output_entry["tags"].append(sector)
            
            logging.debug(f"Added filename tags: '{date_report}' and '{sector}'")
        
        output_list.append(output_entry)
    
    logging.info(f"Processed {len(output_list)} files in output_list")
    

def create_answer():
    """
    Create answer dictionary from output_list in the format:
    {"filename1": "keyword1,keyword2,...", "filename2": "keyword1,keyword2,..."}
    """
    answer = {}
    for entry in output_list:
        # Join all keywords with commas to create a single string
        keyword_string = ",".join(entry["tags"])
        answer[entry["filename"]] = keyword_string
    
    logging.info("Created answer dictionary")
    logging.debug(f"Answer content: {json.dumps(answer, ensure_ascii=False, indent=2)}")
    return answer

def main():
    # Step 1: Process folders and get tags
    if args.start <= 1:
        logging.info("Starting from Step 1: Processing folders and getting tags")
        process_folders()
        dump_results()
        
    # Step 2: Join keywords from both lists
    if args.start <= 2:
        logging.info("Starting Step 2: Joining keywords from fact_list and input_list")
        try:
            # Load existing results if starting from step 2
            if args.start == 2:
                with open(os.path.join(DUMP_FOLDER, 'fact_list.json'), 'r', encoding='utf-8') as f:
                    fact_list.extend(json.load(f))
                with open(os.path.join(DUMP_FOLDER, 'input_list.json'), 'r', encoding='utf-8') as f:
                    input_list.extend(json.load(f))
            
            # Process keyword joining
            join_keywords()
            
            # Dump output_list if in test mode
            
            ensure_dump_folder_exists()
            output_file = os.path.join(DUMP_FOLDER, 'output_list.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_list, f, ensure_ascii=False, indent=2)
            logging.info(f"Dumped output_list to {output_file}")
            
        except FileNotFoundError as e:
            logging.error(f"Required file not found: {e}. Please run from step 1 first.")
            return
    
    # Step 3: Create answer and send to server
    if args.start <= 3:
        logging.info("Starting Step 3: Creating answer and sending to server")
        try:
            # Load existing results if starting from step 3
            if args.start == 3:
                with open(os.path.join(DUMP_FOLDER, 'output_list.json'), 'r', encoding='utf-8') as f:
                    output_list.extend(json.load(f))
            
            # Create answer
            answer = create_answer()
            
            # Dump answer if in test mode
            ensure_dump_folder_exists()
            answer_file = os.path.join(DUMP_FOLDER, 'answer.json')
            with open(answer_file, 'w', encoding='utf-8') as f:
                json.dump(answer, f, ensure_ascii=False, indent=2)
            logging.info(f"Dumped answer to {answer_file}")
            
            # Send answer to server
            response = send_task(args.task, KEYDEVS, answer)
            
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
            logging.error(f"An error occurred in step 3: {e}")
            return

if __name__ == "__main__":
    main() 