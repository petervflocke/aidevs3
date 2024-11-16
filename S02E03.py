import requests
import sys
import os
import json
import logging
import argparse
from openai import OpenAI


SYSTEM_PROMPT = """
Please take the following description as input and create an optimized DALL-E prompt that accurately captures the visual details for image generation. Focus on enhancing key elements essential to the subject, such as its appearance, character, colors, textures, and notable features. Exclude any non-essential background information or unrelated details.
The output must be returned restricted json string like this:{"dalle_prompt": "optimized_prompt_text"}

#Description:
"""

# Set up argument parser
parser = argparse.ArgumentParser(description='AI Devs API script')
parser.add_argument('--debug', choices=['debug', 'info', 'off'], default='off', help='Debug mode')
parser.add_argument('--task', required=True, help='Task name')
args = parser.parse_args()

# Use the task name from command line arguments
TASK = args.task

# Set up logging based on debug mode
if args.debug == "debug":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
elif args.debug == "info":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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

INPUT_ENDPOINT = "https://centrala.ag3nts.org/data/{KEYDEVS}/robotid.json"
AI_DEVS_VERIFY = "https://centrala.ag3nts.org/report"


# Getting description
response = requests.get(INPUT_ENDPOINT.format(KEYDEVS=KEYDEVS))
if response.status_code == 200:
    json_data = response.json()
    logging.info(f"JSON data from {INPUT_ENDPOINT}: {json_data}")
else:
    print(f"Failed to fetch data from {INPUT_ENDPOINT}. Status code: {response.status_code}")


INPUT = json_data.get("description")
DALE_Prompt_txt = ""
if INPUT:
    DALLE_Prompt = []
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.strip()},
            {"role": "user", "content": INPUT}
        ]
    )
    DALE_Prompt_json = response.choices[0].message.content.strip()
    logging.info(f"GPT converted Prompt: {DALE_Prompt_json}")
else:
    print(f"Missing robot's Descritpion")
    sys.exit(1)

if DALE_Prompt_json:
    try:
        DALE_Prompt_txt = json.loads(DALE_Prompt_json).get("dalle_prompt")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        DALE_Prompt_txt = None
        sys.exit(1)

image_url = ""
if DALE_Prompt_txt:
    logging.info(f"Dall-E Prompt: {DALE_Prompt_txt}")
    response = client.images.generate(
        model="dall-e-3",
        prompt=DALE_Prompt_txt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    image_url = response.data[0].url
else:
    print(f"Generating DALLE Prompt failed see {response.data}")
    sys.exit(1)

if image_url:
    logging.info(f"Pic addr: {image_url}")
    data = {
        "task": TASK,
        "apikey": f"{KEYDEVS}",
        "answer": image_url
    }
    logging.info(f"data: {data}")
    response = requests.post(AI_DEVS_VERIFY, json=data)
    json_response = response.json()
    print(json_response)
else:
    print("Error generating pics")

