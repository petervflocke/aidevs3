import openai
import argparse
import logging
import os
import requests
import sys

# Set up argument parser
parser = argparse.ArgumentParser(description='Audio Transcription Script')
parser.add_argument('--file', required=True, help='Path to the audio file')
parser.add_argument('--debug', choices=['debug', 'info', 'off'], default='off', help='Debug mode')
args = parser.parse_args()

# Set up logging based on debug mode
if args.debug == "debug":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
elif args.debug == "info":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
else:
    logging.disable(sys.maxsize)

# Set up the OpenAI API key
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Specify the path to your audio file
file_path = args.file

logging.info(f"Processing audio file: {file_path}")

# Open the audio file in binary mode
with open(file_path, "rb") as audio_file:
    logging.debug("Sending audio file to OpenAI for transcription")
    files = {
        "file": (os.path.basename(file_path), audio_file, "audio/mpeg")
    }
    data = {
        "model": "whisper-1"
    }
    headers = {
        "Authorization": f"Bearer {openai.api_key}"
    }
    response = requests.post("https://api.openai.com/v1/audio/transcriptions", headers=headers, files=files, data=data)
    logging.debug(f"Response from API: {response.text}")
    try:
        transcript = response.json()["text"]
    except KeyError:
        logging.error("Error: 'text' key not found in API response")
        transcript = ""

# Save the transcript to a text file
output_file = os.path.splitext(args.file)[0] + '.txt'
with open(output_file, "w", encoding="utf-8") as text_file:
    text_file.write(transcript)

logging.info(f"Transcript saved to {output_file}")