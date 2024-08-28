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

INPUT_ENDPOINT = "https://poligon.aidevs.pl/dane.txt"
AI_DEVS_VERIFY = "https://poligon.aidevs.pl/verify"

if not KEY:
    raise ValueError("API KEY cannot be empty, setup environment variable AIDEVS")
if not AI_DEVS_VERIFY:
    raise ValueError("URL for AI_devs cannot be empty, setup environment variable URL_AI_DEVS")

# Remove or comment out this line if not needed
# logging.debug(f"Key: {KEY}\nTaskName:{TASKNAME}")

response = requests.get(INPUT_ENDPOINT)
if response.status_code == 200:
    text_content = response.text.strip()
    logging.info(f"Received data: {text_content}")
    ANSWER = text_content.split('\n')
    logging.info(f"Parsed answer: {ANSWER}")
else:
    logging.error(f"Failed to fetch data. Status code: {response.status_code}")
    ANSWER = []

if ANSWER:
    data = {
        "task": TASK,
        "apikey": f"{KEY}",
        "answer": ANSWER 
    }
    logging.info(f"Data: {data}")

response = requests.post(AI_DEVS_VERIFY, json=data)
json_response = response.json()
print(json_response)