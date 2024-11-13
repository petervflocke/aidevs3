import os
import sys
import json
import argparse
import requests
from openai import OpenAI
import logging

# Define the system prompt for OpenAI
SYSTEM_PROMPT = """
Anonymize the following text by replacing any instance of sensitive information with the word "CENZURA".

### The sensitive is define by:
Full name - first name and last name, replace with one word "CENZURA"
Street name and number, replace with one word "CENZURA"
Cities
Ages
Maintain all punctuation, spacing, and the original structure exactly as they appear. Do not rephrase or add explanations—output only the anonymized text.
Output only the anonymized text in json format.

### Conversion example:
Input: "Dane personalne podejrzanego: Wojciech Górski. Przebywa w Lublinie, ul. Akacjowa 7. Wiek: 27 lat."
Output: {{"result": "Dane personalne podejrzanego: CENZURA. Przebywa w CENZURA, ul. CENZURA. Wiek: CENZURA lat."}}

### Task:
Apply these rules to the following text: {INPUT}
"""

class OllamaLLM:
    def __init__(self, host: str = "http://localhost", port: int = 11434):
        self.host = host
        self.port = port

    def _call(self, input: str) -> str:
        base_url = f"{self.host}:{self.port}/api/generate"
        headers = {"Content-Type": "application/json"}
        logging.debug(f"Local prompt: {SYSTEM_PROMPT.format(INPUT=input)}")

        response = requests.post(
            base_url,
            headers=headers,
            json={
                "model": "llama3:8b", 
                #"model": "llama2:7b",
                "prompt": SYSTEM_PROMPT.format(INPUT=input),
                "stream": False,
                "format": "json",
                "system": "respond in format {'result':'...'}"
            }
        )

        if response.status_code == 200:
            return response.json()["response"]
        else:
            raise ValueError(f"Failed to fetch response: {response.text}")

# Set up argument parser
parser = argparse.ArgumentParser(description='AI Devs API script')
parser.add_argument('--debug', choices=['debug', 'info', 'off'], default='off', help='Debug mode')
parser.add_argument('--llm', choices=['local', 'public'], required=True, help='LLM to use')
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

# Initialize the LLM client based on the selected option
if args.llm == "local":
    llm = OllamaLLM(host="http://localhost", port=11434)
    llm_call = llm._call
else:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    llm_call = lambda prompt: client.chat.completions.create(
        model="gpt-4o-mini",
        #model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.strip()},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=200
    ).choices[0].message.content.strip()

# Process each line in the file
anonymized_lines = []
for line in file_content:
    logging.info(f"Processing line: {line}")
    # Call the LLM API to anonymize the line
    try:
        anonymized_line = llm_call(line)
        anonymized_text = json.loads(anonymized_line).get("result")
        if anonymized_text:
            anonymized_lines.append(anonymized_text)
        else:
            logging.error(f"The JSON response does not contain the 'result' key: {anonymized_line}")
            sys.exit(1)
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON response: {anonymized_line}")
        sys.exit(1)
    logging.info(f"Anonymized line: {anonymized_lines[-1]}")

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