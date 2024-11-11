import openai
import argparse
import logging
import os

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
openai.api_key = "YOUR_API_KEY"

# Specify the path to your audio file
file_path = args.file

logging.info(f"Processing audio file: {file_path}")

# Open the audio file in binary mode
with open(file_path, "rb") as audio_file:
    logging.debug("Sending audio file to OpenAI for transcription")
    transcript = openai.Audio.transcribe("whisper-1", audio_file.read())

# Save the transcript to a text file
output_file = os.path.splitext(args.file)[0] + '.txt'
with open(output_file, "w", encoding="utf-8") as text_file:
    text_file.write(transcript["text"])

logging.info(f"Transcript saved to {output_file}")