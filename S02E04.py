import requests
import sys
import os
import json
import logging
import argparse
from openai import OpenAI
import base64

# Prompts for OpenAI
TEXT_CLASSIFICATION_PROMPT = """
Please classify the following INPUT text according to whether it contains information about captured people or signs of their presence ('people'), 
information about hardware repairs ('hardware'), or none of these ('none'). 
Ignore any notes related to module or software issues, updates or other topics. 
Respond only in JSON, without any additional formatting or strings, as follows: {"classification":"result"}.

###INPUT
"""

IMAGE_DESCRIPTION_PROMPT = "Describe the contents of this image in detail."
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
    #logging.getLogger('openai').setLevel(logging.WARNING)
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

# Function to transcribe audio file
def transcribe_audio(file_path):
    with open(file_path, "rb") as audio_file:
        logging.debug("Sending audio file to OpenAI for transcription")
        files = {
            "file": (os.path.basename(file_path), audio_file, "audio/mpeg")
        }
        data = {
            "model": "whisper-1"
        }
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        response = requests.post("https://api.openai.com/v1/audio/transcriptions", headers=headers, files=files, data=data)
        logging.debug(f"Response from API: {response.text}")
        try:
            transcript = response.json()["text"]
        except KeyError:
            logging.error("Error: 'text' key not found in API response")
            transcript = ""
    return transcript

# Function to classify text or audio transcript
def classify_text(text):
    logging.verbose(f"Sending text to OpenAI for classification: {text}")

    if args.debug == "verbose":
        # Get the root logger
        root_logger = logging.getLogger()
        # Store the current logging level
        previous_logging_level = root_logger.level
        # Temporarily disable logging
        root_logger.setLevel(logging.CRITICAL)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": TEXT_CLASSIFICATION_PROMPT},
            {"role": "user", "content": text}
        ]
    )
    # Restore the previous logging configuration
    if args.debug == "verbose":
        root_logger.setLevel(previous_logging_level)

    logging.debug(f"Response from API: {response.choices[0].message.content.strip()}")
    classification = response.choices[0].message.content.strip()
    logging.verbose(f"Classification: {classification}")

    return json.loads(classification)["classification"]

# Function to encode image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Function to describe image
def describe_image(image_path):
    base64_image = encode_image(image_path)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": IMAGE_DESCRIPTION_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ],
        "max_tokens": 300
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    response_json = response.json()
    logging.debug(f"Response from API: {response_json['choices'][0]['message']['content']}")
    image_description = response_json["choices"][0]["message"]["content"]
    return image_description

# Classify files in the folder
folder_path = args.folder
file_classifications = {"people": [], "hardware": []}

for filename in sorted(os.listdir(folder_path)):
    logging.verbose(f"File: {filename}")
    file_path = os.path.join(folder_path, filename)
    extension = os.path.splitext(filename)[1].lower()
    if extension == ".txt":
        with open(file_path, "r", encoding="utf-8") as file:
            text = file.read()
            classification = classify_text(text)
    elif extension == ".mp3":
        transcript = transcribe_audio(file_path)
        classification = classify_text(transcript)
    elif extension == ".png":
        image_description = describe_image(file_path)
        classification = classify_text(image_description)
    else:
        logging.verbose(f"Skipping file with unsupported extension: {filename}")
        continue
    
    if classification == "people":
        file_classifications["people"].append(filename)
    elif classification == "hardware":
        file_classifications["hardware"].append(filename)

logging.verbose(f"File classifications: {file_classifications}")

data = {
    "task": TASK,
    "apikey": f"{KEYDEVS}",
    "answer": file_classifications
}
logging.verbose(f"data: {data}")
response = requests.post(AI_DEVS_VERIFY, json=data)
json_response = response.json()
print(json_response)

