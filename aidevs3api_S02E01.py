import requests
import sys
import os
import json
import logging
import argparse

# Set up argument parser
parser = argparse.ArgumentParser(description='AI Devs API script')
parser.add_argument('--debug', choices=['debug', 'info', 'off'], default='off', help='Debug mode')
parser.add_argument('--task', required=True, help='Task name')
parser.add_argument('--file', required=True, help='File to upload')
args = parser.parse_args()

# Set up logging based on debug mode
if args.debug == "debug":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
elif args.debug == "info":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
else:
    logging.disable(sys.maxsize)

# Use the task name from command line arguments
TASK = args.task
logging.info(f"Task name: {TASK}")

KEY = os.environ.get('AIDEVS')

AI_DEVS_VERIFY = "https://centrala.ag3nts.org/report"

if not KEY:
    raise ValueError("API KEY cannot be empty, setup environment variable AIDEVS")
if not AI_DEVS_VERIFY:
    raise ValueError("URL for AI_devs cannot be empty, setup environment variable URL_AI_DEVS")

# Read the file content and store it in the ANSWER variable
with open(args.file, 'r') as f:
    ANSWER = f.read()

data = {
    "task": TASK,
    "apikey": f"{KEY}",
    "answer": ANSWER
}
print(data)
response = requests.post(AI_DEVS_VERIFY, json=data)
json_response = response.json()
print(json_response)
