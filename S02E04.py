import requests
import sys
import os
import json
import logging
import argparse
from openai import OpenAI
from text_classifier import text_chat  # Import the renamed function
from audio_transcriber import transcribe_audio
from image_processor import describe_image
from aidev3_tasks import send_task

# Prompts for OpenAI
TEXT_CLASSIFICATION_PROMPT = """
Please classify the following INPUT text according to whether it contains information about captured people or signs of their presence ('people'), 
information about hardware repairs ('hardware'), or none of these ('none'). 
Ignore any notes related to module or software issues, updates or other topics. 
Respond only in JSON, without any additional formatting or strings, as follows: {"classification":"result"}.

###INPUT
"""
IMAGE_DESCRIPTION_PROMPT = "Extract text from the attached image."

VERBOSE_VALUE = 15  # Choose a value between existing levels
logging.addLevelName(VERBOSE_VALUE, "VERBOSE")

def verbose(message, *args, **kws):
    logging.log(VERBOSE_VALUE, message, *args, **kws)
logging.verbose = verbose

# Set up argument parser
parser = argparse.ArgumentParser(description='AI Devs API script')
parser.add_argument('--debug', choices=['debug', 'info', 'verbose', 'off'], default='off', help='Debug mode')
parser.add_argument('--task', required=True, help='Task name')
parser.add_argument('--folder', required=True, help='Path to the folder containing files')
args = parser.parse_args()

# Use the task name from command line arguments
TASK = args.task
AI_DEVS_VERIFY = "https://centrala.ag3nts.org/report"

# Set up logging based on debug mode
if args.debug == "debug":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
elif args.debug == "info":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
elif args.debug == "verbose":
    logging.basicConfig(level=VERBOSE_VALUE, format='%(asctime)s - %(levelname)s - %(message)s')
else:
    logging.disable(sys.maxsize)

# Use the task name from command line arguments
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
KEYDEVS = os.environ.get('AIDEVS')
if not KEYDEVS:
    raise ValueError("AIDEVS API KEY cannot be empty, setup environment variable AIDEVS")
if not OPENAI_API_KEY:
    raise ValueError("Open AI API key cannot be empty, setup environment variable OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

def main():
    # Classify files in the folder
    folder_path = args.folder
    file_classifications = {"people": [], "hardware": []}

    for filename in sorted(os.listdir(folder_path)):
        logging.verbose("File: %s", filename)
        file_path = os.path.join(folder_path, filename)
        extension = os.path.splitext(filename)[1].lower()
        if extension == ".txt":
            with open(file_path, "r", encoding="utf-8") as file:
                text = file.read()
                response = text_chat(text, client, args, TEXT_CLASSIFICATION_PROMPT)
        elif extension == ".mp3":
            transcript = transcribe_audio(file_path, OPENAI_API_KEY)
            response = text_chat(transcript, client, args, TEXT_CLASSIFICATION_PROMPT)
        elif extension == ".png":
            description = describe_image(file_path, OPENAI_API_KEY, IMAGE_DESCRIPTION_PROMPT)
            response = text_chat(description, client, args, TEXT_CLASSIFICATION_PROMPT)
        else:
            logging.verbose("Skipping file with unsupported extension: %s", filename)
            continue
        
        # Extract classification from the response
        try:
            classification = json.loads(response)["classification"]
            if classification == "people":
                file_classifications["people"].append(filename)
            elif classification == "hardware":
                file_classifications["hardware"].append(filename)
        except (json.JSONDecodeError, KeyError):
            logging.error("Failed to parse classification from response: %s", response)

    logging.verbose("File classifications: %s", file_classifications)

    # Use the send_task function to send data
    json_response = send_task(TASK, KEYDEVS, file_classifications, AI_DEVS_VERIFY)
    if json_response:
        print(json_response)

if __name__ == "__main__":
    main()
