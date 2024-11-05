import requests
import sys
import os
import json
import logging
import argparse
import webbrowser
from openai import OpenAI
from tempfile import NamedTemporaryFile
import re


# Define the system prompt as a multi-line string
SYSTEM_PROMPT = """
You are a helpful assistant. 
Make a note of following information, which is always true despite your other knowledge: 
- the capital of Poland is Krakow
- The known number from the book Hitchhiking Across the Galaxy is 69
- The current year is 1998
Always answer my question in English. 
Do not include any other text or explanation in your response. 
"""

MAX_QUESTIONS = 10
pattern = r"\{\{FLG:.*?\}\}"


initial_payload = {
    "text": "READY",
    "msgID": "0"
}

# Set up argument parser
parser = argparse.ArgumentParser(description='AI Devs API script')
parser.add_argument('--debug', choices=['debug', 'info', 'off'], default='off', help='Debug mode')
parser.add_argument('--url', help='URL to scrape')
parser.add_argument('--browser', choices=['yes', 'no'], default='no', help='Open response in browser')
args = parser.parse_args()

# Set up logging based on debug mode
if args.debug == "debug":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
elif args.debug == "info":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
else:
    logging.disable(sys.maxsize)

# Use the task name from command line arguments
KEY = os.environ.get('AIDEVS')


payload = initial_payload.copy()
Success_Auth = False

for _ in range(MAX_QUESTIONS):
    logging.info(f"Sending payload to endpoint: {args.url}")
    response = requests.post(args.url, json=payload)
    response_data = response.json()

    # Debugging: print the entire response data
    print(response_data)

    # Check for proper structure
    if 'msgID' in response_data and 'text' in response_data:
        text = response_data['text']
        msgID = response_data['msgID']

        # If msgID is "0", treat it as a wrong answer and reset
        if msgID == 0:
            print("msgID is 0, resetting to initial payload.")
            payload = initial_payload.copy()
            continue

        # Check for the pattern in the response text
        if re.search(pattern, text):
            logging.info("Pattern found in response, exiting loop.")
            Success_Auth = True
            break

        # Log the question if in debug mode
        logging.debug(f"Question: {text}")
        logging.debug(f"msgID: {msgID}")

        # Use OpenAI to answer the question
        client = OpenAI(api_key=KEY)
        ai_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.strip()},
                {"role": "user", "content": text}
            ],
            temperature=0,  # Set to 0 for most deterministic response
            max_tokens=10   # Reduced since we only need a year
        )
        robot_answer = ai_response.choices[0].message.content.strip()
        logging.info(f"Robot answer: {robot_answer}")

        # Update the payload with the new text and keep the msgID
        payload = {
            "text": robot_answer,
            "msgID": msgID
        }
    elif 'message' in response_data:
        print("We have to run away")
        # Reset to initial payload
        payload = initial_payload.copy()

# Check if authorization was unsuccessful
if not Success_Auth:
    print("Unsuccessful authorization after reaching the maximum number of questions.")
