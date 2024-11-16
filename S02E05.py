import sys
import os
import logging
import argparse
import requests
from aidev3_tasks import fetch_file
import urllib.parse
import shutil
from markdownify import MarkdownConverter
from aidev3_tasks import fetch_file
from image_processor import describe_image
from audio_transcriber import transcribe_audio
import json
from text_classifier import text_chat
from openai import OpenAI
from aidev3_tasks import send_task

# Set up argument parser
parser = argparse.ArgumentParser(description='AI Devs API script for fetching and processing data')
parser.add_argument('--debug', choices=['debug', 'info', 'verbose', 'off'], default='off', help='Debug mode')
parser.add_argument('--task', required=True, help='Task name')
parser.add_argument('--url', required=True, help='URL to fetch the text from')
parser.add_argument('--start', type=int, choices=[1, 2, 3], default=1, 
                    help='Start from step: 1-scraping, 2-questioning, 3-sending task')
args = parser.parse_args()

# Set up logging
VERBOSE_VALUE = 15  # Choose a value between existing levels
logging.addLevelName(VERBOSE_VALUE, "VERBOSE")
def verbose(message, *args, **kws):
    logging.log(VERBOSE_VALUE, message, *args, **kws)
logging.verbose = verbose
if args.debug == "debug":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
elif args.debug == "info":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
elif args.debug == "verbose":
    logging.basicConfig(level=VERBOSE_VALUE, format='%(asctime)s - %(levelname)s - %(message)s')
else:
    logging.disable(sys.maxsize)

def ensure_multimedia_folder_exists():
    """Ensure the 'multimedia' folder exists."""
    if not os.path.exists('multimedia'):
        os.makedirs('multimedia')
        logging.info("Created 'multimedia' directory.")
    else:
        logging.info("'multimedia' directory already exists.")

def download_media_file(url, base_url):
    """Download media file and maintain original folder structure."""
    if not url.startswith(('http://', 'https://')):
        url = urllib.parse.urljoin(base_url, url)
        # Get the relative path from the URL
        relative_path = urllib.parse.urlparse(url).path
        if relative_path.startswith('/'):
            relative_path = relative_path[1:]
    else:
        relative_path = os.path.basename(urllib.parse.urlparse(url).path)
    
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            # Create full path including subdirectories
            full_path = os.path.join('multimedia', relative_path)
            
            # Create subdirectories if they don't exist
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Save the file
            with open(full_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
            logging.info(f"Downloaded media file: {full_path}")
            return relative_path  # Return relative path for markdown links
    except Exception as e:
        logging.error(f"Failed to download media file {url}: {str(e)}")
    return None

class CustomMarkdownConverter(MarkdownConverter):
    def convert_h2(self, el, text, convert_as_inline):
        """Convert h2 elements to markdown with extra spacing."""
        return f'\n\n## {text}\n\n'

    def convert_figure(self, el, text, convert_as_inline):
        """Convert figure elements to markdown with local media files and add image description."""
        img_tag = el.find('img')
        if img_tag:
            src = img_tag.get('src')
            alt_text = img_tag.get('alt', '')
            
            # Download the image and get relative path
            relative_path = download_media_file(src, base_url)
            if relative_path:
                # Get the full path to the downloaded image
                full_path = os.path.join('multimedia', relative_path)
                
                # Get image description from OpenAI
                api_key = os.environ.get('OPENAI_API_KEY')
                prompt = "Describe this image in detail, focusing on what it shows and its context."
                image_description = describe_image(full_path, api_key, prompt)
                
                markdown_image = f'![{alt_text}](multimedia/{relative_path})\n'
                
                # Handle caption if present
                figcaption = el.find('figcaption')
                if figcaption:
                    caption = figcaption.text.strip()
                    return f'{markdown_image}*{caption}*\n\n**Zawartość grafiki:** {image_description}\n\n'
                return f'{markdown_image}\n**Zawartość grafiki:** {image_description}\n\n'
        return ''

    def convert_audio(self, el, text, convert_as_inline):
        """Remove source elements from markdown."""
        return ''

    def convert_a(self, el, text, convert_as_inline):
        """Convert anchor elements, with special handling for downloadable media files."""
        # Check if this is a downloadable link
        if el.get('download') is not None:
            href = el.get('href')
            if href and (href.endswith('.mp3') or href.endswith('.wav')):
                # Download the audio file
                relative_path = download_media_file(href, base_url)
                if relative_path:
                    # Get the full path to the downloaded audio file
                    full_path = os.path.join('multimedia', relative_path)
                    
                    # Get audio transcription from OpenAI
                    api_key = os.environ.get('OPENAI_API_KEY')
                    transcript = transcribe_audio(full_path, api_key)
                    
                    return f'\n\n[🔊 {text}](multimedia/{relative_path})\n\n**Transkrypcja pliku audio:** {transcript}\n\n'
        
        # For non-media links, use default conversion
        return super().convert_a(el, text, convert_as_inline)

    def convert_style(self, el, text, convert_as_inline):
        """Remove style elements by returning empty string."""
        return ''

# Create shorthand method for conversion
def md(html, **options):
    return CustomMarkdownConverter(**options).convert(html)

def fetch_and_process_webpage(url):
    """Fetch the web page from the given URL and download multimedia files."""
    response = requests.get(url)
    if response.status_code == 200:
        logging.info("Successfully fetched the web page.")
        
        # Store the base URL for resolving relative paths
        global base_url
        base_url = url
        
        # Save the raw HTML content to a file for debugging
        html_output_file = os.path.join('multimedia', 'source.html')
        with open(html_output_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        logging.info(f"Saved raw HTML content to {html_output_file}")
        
        # Convert HTML directly to markdown using the custom converter
        markdown_text = md(
            response.text,
            extras=['tables', 'fenced-code-blocks']
        )
        
        # Save markdown content to file
        markdown_output_file = os.path.join('multimedia', 'content.md')
        with open(markdown_output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_text)
        
        logging.info(f"Saved markdown content to {markdown_output_file}")
        return markdown_text
    else:
        logging.error(f"Failed to fetch the web page. Status code: {response.status_code}")
        return None

def process_questions_and_content(questions_dict, markdown_content, args):
    """Process questions and markdown content using OpenAI."""

    # Define the prompt template
    PROMPT = """
    Given the text in markdown format below, please provide a one-sentence answer for each question listed.
    Respond in a JSON format with answers corresponding to each question ID.
    Do not add any formatting or other comments.

    {questions}

    Given the text below, please provide a one-sentence answer for each question listed.
    Respond in a JSON format with answers corresponding to each question ID.
    Do not add any formatting like ```json``` or other comments.

    Text:
    """

    # Convert questions dictionary to JSON string
    questions_json = json.dumps(questions_dict, ensure_ascii=False, indent=2)
    
    # Create the complete prompt by replacing placeholder
    complete_prompt = PROMPT.format(questions=questions_json)
    
    # Initialize OpenAI client
    client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    
    # Get response from OpenAI
    response = text_chat(markdown_content, client, args, complete_prompt)
    
    # Save the response to a JSON file in the multimedia folder
    answers_file = os.path.join('multimedia', 'answers.json')
    with open(answers_file, 'w', encoding='utf-8') as f:
        f.write(response)
    
    logging.info(f"Answers saved to {answers_file}")
    return response

def main():
    # Ensure the multimedia folder exists
    ensure_multimedia_folder_exists()

    # Fetch the file from the hardcoded endpoint
    api_key = os.environ.get('AIDEVS')
    if not api_key:
        raise ValueError("AIDEVS API KEY cannot be empty, setup environment variable AIDEVS")

    # Step 1: Fetch questions and scrape webpage
    if args.start <= 1:
        logging.info("Starting from Step 1: Fetching questions and scraping webpage")
        # Hardcoded endpoint for fetching the file
        endpoint = "arxiv.txt"
        file_content = fetch_file(api_key, endpoint)

        if file_content:
            logging.info("Fetched content: %s", file_content)
            
            # Translate the fetched content into a Python dictionary
            questions_dict = {}
            for line in file_content:
                if '=' in line:
                    key, value = line.split('=', 1)
                    questions_dict[key] = value
            
            logging.info("Translated questions: %s", questions_dict)
            
            # Save questions_dict for later use
            questions_file = os.path.join('multimedia', 'questions.json')
            with open(questions_file, 'w', encoding='utf-8') as f:
                json.dump(questions_dict, f, ensure_ascii=False, indent=2)
            
            # Fetch and process the web page
            markdown_content = fetch_and_process_webpage(args.url)
        else:
            logging.error("Failed to fetch content from the URL")
            return
    
    # Step 2: Process questions with OpenAI
    if args.start <= 2:
        logging.info("Starting Step 2: Processing questions with OpenAI")
        try:
            # Load existing markdown content if starting from step 2
            if args.start == 2:
                with open(os.path.join('multimedia', 'content.md'), 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
                with open(os.path.join('multimedia', 'questions.json'), 'r', encoding='utf-8') as f:
                    questions_dict = json.load(f)
            
            # Process questions and content
            process_questions_and_content(questions_dict, markdown_content, args)
        except FileNotFoundError as e:
            logging.error(f"Required file not found: {e}. Please run from step 1 first.")
            return
    
    # Step 3: Send task
    if args.start <= 3:
        logging.info("Starting Step 3: Sending task")
        try:
            # Read the answers from the JSON file
            answers_file = os.path.join('multimedia', 'answers.json')
            with open(answers_file, 'r', encoding='utf-8') as f:
                answers = json.load(f)
            
            # Send the answers to the server
            response = send_task(args.task, api_key, answers)
            
            if response:
                if response.get('code') == 0:
                    print("Task completed successfully!")
                    print("Server response:", response.get('message', 'No message provided'))
                else:
                    print("Task failed with error:", response.get('message', 'Unknown error'))
            else:
                print("Failed to get response from server")
                
        except FileNotFoundError as e:
            print(f"Required file not found: {e}. Please run from earlier step first.")
            return
        except json.JSONDecodeError as e:
            print(f"Failed to parse answers.json: {e}")
            return
        except Exception as e:
            print(f"An error occurred while sending the task: {e}")
            return

if __name__ == "__main__":
    main() 