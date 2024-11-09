import os
import sys
import json
import argparse
import requests
from openai import OpenAI
import logging

# Define the system prompt for OpenAI
SYSTEM_PROMPT = """
Anonymize the following text by replacing any instance of sensitive information with the word "CENZURA". This includes:

Full names (first name and last name)
Street names with house numbers
Cities
Ages
Maintain all punctuation, spacing, and the original structure exactly as they appear. Do not rephrase or add explanations—output only the anonymized text.

Example:

Input: "Dane personalne podejrzanego: Wojciech Górski. Przebywa w Lublinie, ul. Akacjowa 7. Wiek: 27 lat."
Output: "Dane personalne podejrzanego: CENZURA. Przebywa w CENZURA, ul. CENZURA. Wiek: CENZURA lat."

Now, apply these rules to the following text: {INPUT}
"""

# Set up argument parser
parser = argparse.ArgumentParser(description='AI Devs API script')
parser.add_argument('--debug', choices=['debug', 'info', 'off'], default='off', help='Debug mode')
args = parser.parse_args()

# Set up logging based on debug mode
if args.debug == "debug":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
elif args.debug == "info":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
else:
    logging.disable(sys.maxsize)

# Get the API key from the environment variable
KEY = os.environ.get('AIDEVS')

# Check if the API key is available
if not KEY:
    raise ValueError("API KEY cannot be empty, setup environment variable AIDEVS")

# URL to fetch the file
FILE_URL = f"https://centrala.ag3nts.org/data/{KEY}/cenzura.txt"
logging.info(f"Fetching file from: {FILE_URL}")

# URL to report the results
REPORT_URL = "https://centrala.ag3nts.org/report"

# Fetch the file from the URL
response = requests.get(FILE_URL)
if response.status_code == 200:
    file_content = response.text.splitlines()
    logging.info(f"File fetched successfully. Number of lines: {len(file_content)}")
else:
    raise ValueError(f"Failed to fetch the file. Error: {response.status_code}")

# Initialize the OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Process each line in the file
anonymized_lines = []
for line in file_content:
    logging.info(f"Processing line: {line}")
    # Call the OpenAI API to anonymize the line
    ai_response = client.chat.completions.create(
        #model="gpt-4o-mini",
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.strip()},
            {"role": "user", "content": line}
        ],
        temperature=0,  # Set to 0 for most deterministic response
        max_tokens=100  # Adjust as needed
    )
    anonymized_line = ai_response.choices[0].message.content.strip()
    anonymized_lines.append(anonymized_line)
    logging.info(f"Anonymized line: {anonymized_line}")


sys.exit(0)

# Prepare the payload for the report
payload = {
    "task": "CENZURA",
    "apikey": KEY,
    "answer": "\n".join(anonymized_lines)
}


# Send the report to the endpoint
logging.info(f"Sending report to: {REPORT_URL}")
logging.info(f"Payload: {payload}")
response = requests.post(REPORT_URL, json=payload)
if response.status_code == 200:
    logging.info("Report submitted successfully.")
else:
    logging.info(f"Failed to submit the report. Error: {response.status_code}")
logging.info(f"Central response: {response.json()}")
