import sys
import os
import logging
import argparse
import requests
from aidev3_tasks import fetch_file
import urllib.parse
import shutil
from markdownify import MarkdownConverter
from aidev3_tasks import fetch_file
from image_processor import describe_image
from audio_transcriber import transcribe_audio
import json
from text_classifier import text_chat
from openai import OpenAI
from aidev3_tasks import send_task
import jsonlines
from datetime import datetime

# Set up argument parser
parser = argparse.ArgumentParser(description='AI Devs API script for fetching and processing data')
parser.add_argument('--debug', choices=['debug', 'info', 'verbose', 'off'], default='off', help='Debug mode')
parser.add_argument('--task', required=True, help='Task name')
# End of Selection
parser.add_argument('--start', type=int, choices=[1, 2, 3], default=1, 
                    help='Start from step: 1-scraping, 2-questioning, 3-sending task')
args = parser.parse_args()

# Set up logging
VERBOSE_VALUE = 15  # Choose a value between existing levels
logging.addLevelName(VERBOSE_VALUE, "VERBOSE")
def verbose(message, *args, **kws):
    logging.log(VERBOSE_VALUE, message, *args, **kws)
logging.verbose = verbose
if args.debug == "debug":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
elif args.debug == "info":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
elif args.debug == "verbose":
    logging.basicConfig(level=VERBOSE_VALUE, format='%(asctime)s - %(levelname)s - %(message)s')
else:
    logging.disable(sys.maxsize)

DATA_FOLDER = "S04E02"
CORRECT_FILE = "correct.txt"
INCORRECT_FILE = "incorrect.txt"
VERIFY_FILE = "verify_no_lines.txt"
TRAINING_FILE = "training_data.jsonl"

# API Keys setup
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
KEYDEVS = os.environ.get('AIDEVS')
if not KEYDEVS:
    raise ValueError("AIDEVS API KEY cannot be empty, setup environment variable AIDEVS")
if not OPENAI_API_KEY:
    raise ValueError("Open AI API key cannot be empty, setup environment variable OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

def validate_line(line):
    """Validate if line matches expected pattern: four comma-separated numbers"""
    try:
        # Remove whitespace and split by comma
        values = line.strip().split(',')
        
        # Check if we have exactly 4 numbers
        if len(values) != 4:
            return None
            
        # Convert all values to integers and validate
        numbers = [int(val) for val in values]
        
        # Optional: Add additional validation rules here
        # For example, check if numbers are within expected range
        # if not all(-100 <= n <= 100 for n in numbers):
        #     return None
        
        # Return cleaned line
        return ','.join(str(n) for n in numbers)
    except (ValueError, TypeError):
        return None

def prepare_training_data():
    """Prepare JSONL training data from correct and incorrect files with validation"""
    training_data = []
    skipped_lines = 0
    
    # Read correct examples
    with open(os.path.join(DATA_FOLDER, CORRECT_FILE), 'r', encoding='utf-8') as f:
        correct_texts = f.readlines()
        for line_num, text in enumerate(correct_texts, 1):
            cleaned_text = validate_line(text)
            if cleaned_text is None:
                logging.warning(f"Skipping invalid line {line_num} in {CORRECT_FILE}: {text.strip()}")
                skipped_lines += 1
                continue
                
            training_data.append({
                "messages": [
                    {"role": "system", "content": "Check the pattern for correctness"},
                    {"role": "user", "content": cleaned_text},
                    {"role": "assistant", "content": "correct"}
                ]
            })
    
    # Read incorrect examples
    with open(os.path.join(DATA_FOLDER, INCORRECT_FILE), 'r', encoding='utf-8') as f:
        incorrect_texts = f.readlines()
        for line_num, text in enumerate(incorrect_texts, 1):
            cleaned_text = validate_line(text)
            if cleaned_text is None:
                logging.warning(f"Skipping invalid line {line_num} in {INCORRECT_FILE}: {text.strip()}")
                skipped_lines += 1
                continue
                
            training_data.append({
                "messages": [
                    {"role": "system", "content": "Check the pattern for correctness"},
                    {"role": "user", "content": cleaned_text},
                    {"role": "assistant", "content": "incorrect"}
                ]
            })
    
    logging.info(f"Total lines skipped due to validation: {skipped_lines}")
    logging.info(f"Total valid training examples: {len(training_data)}")
    
    # Save as JSONL
    jsonl_path = os.path.join(DATA_FOLDER, TRAINING_FILE)
    with jsonlines.open(jsonl_path, mode='w') as writer:
        writer.write_all(training_data)
    
    return jsonl_path

def create_fine_tune(training_file_path):
    """Create fine-tuning job with OpenAI"""
    try:
        # Upload the training file
        with open(training_file_path, 'rb') as f:
            response = client.files.create(
                file=f,
                purpose="fine-tune"
            )
        file_id = response.id
        
        # Create fine-tuning job
        job = client.fine_tuning.jobs.create(
            training_file=file_id,
            model="gpt-3.5-turbo",
            suffix=f"classifier-{datetime.now().strftime('%Y%m%d')}"
        )
        
        return job.id
    except Exception as e:
        logging.error(f"Fine-tuning creation failed: {str(e)}")
        raise

def verify_with_model(model_id):
    """Verify data using fine-tuned model"""
    try:
        with open(os.path.join(DATA_FOLDER, VERIFY_FILE), 'r', encoding='utf-8') as f:
            verify_texts = f.readlines()
        
        results = []
        for text in verify_texts:
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": text.strip()}]
            )
            results.append({
                "text": text.strip(),
                "classification": response.choices[0].message.content
            })
        
        return results
    except Exception as e:
        logging.error(f"Verification failed: {str(e)}")
        raise

def main():
    # Step 1: prepare fine tuning 
    if args.start <= 1:
        logging.info("Starting from Step 1: Preparing training data")
        training_file = prepare_training_data()
        logging.info(f"Training data saved to {training_file}")
        return
    
    # Step 2: use OpenAI to fine tune model
    if args.start <= 2:
        logging.info("Starting Step 2: Processing fine tuning with OpenAI")
        training_file = os.path.join(DATA_FOLDER, TRAINING_FILE)
        job_id = create_fine_tune(training_file)
        logging.info(f"Fine-tuning job created with ID: {job_id}")
        return
    
    # Step 3: Verify data  
    if args.start <= 3:
        logging.info("Starting Step 3: Verify data")
        # Note: You'll need to replace with your actual fine-tuned model ID
        model_id = "ft:gpt-3.5-turbo-0125:personal:classifier-20241126:AXwqrDWQ"
        results = verify_with_model(model_id)
        logging.info("Verification results:", results)
        return

if __name__ == "__main__":
    main() 