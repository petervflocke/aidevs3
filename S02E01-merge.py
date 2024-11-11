import argparse
import glob
import logging
import os
import sys

# Set up argument parser
parser = argparse.ArgumentParser(description='Audio Transcription Script')
parser.add_argument('--debug', choices=['debug', 'info', 'off'], default='off', help='Debug mode')
parser.add_argument('--files', required=True, help='Path to the text files')
parser.add_argument('--output', required=True, help='Path to the output file')
args = parser.parse_args()

# Set up logging based on debug mode
if args.debug == "debug":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
elif args.debug == "info":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
else:
    logging.disable(sys.maxsize)

# Process files
with open(args.output, 'w') as output_file:
    for file_path in glob.glob(args.files):
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        logging.info(f"Processing file: {file_path}")  # Debug message
        output_file.write(f"<{file_name}>\n")
        with open(file_path, 'r') as input_file:
            content = input_file.read()
            output_file.write(content)
        output_file.write(f"</{file_name}>\n")