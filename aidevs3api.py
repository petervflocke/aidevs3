import requests
import sys
import os
import json
import logging

if len(sys.argv) > 1:
    DEBUG_MODE=sys.argv[1]
else:
    #DEBUG_MODE = "debug", "info", anything else for off
    DEBUG_MODE="off"
if DEBUG_MODE == "debug":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
elif DEBUG_MODE == "info":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
else:
    logging.disable(sys.maxsize)

# TASKNAME = os.path.splitext(os.path.basename(__file__))[0]
# logging.info(f"Task name: {TASKNAME}")

KEY = os.environ.get('AIDEVS')

INPUT_ENDPOINT = "https://poligon.aidevs.pl/dane.txt"
AI_DEVS_VERIFY = "https://poligon.aidevs.pl/verify"

TASK = "POLIGON"


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