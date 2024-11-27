import os
import logging
import requests
import urllib.parse
import shutil
from markdownify import MarkdownConverter
from openai import OpenAI
from image_processor import describe_image
from audio_transcriber import transcribe_audio
from typing import Optional, List, Dict
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import json
import argparse
from text_classifier import text_chat
import sys

# Configuration
DUMP_FOLDER = 'C04E03'

VERBOSE_VALUE = 15  # Choose a value between existing levels
logging.addLevelName(VERBOSE_VALUE, "VERBOSE")

def verbose(message, *args, **kws):
    logging.log(VERBOSE_VALUE, message, *args, **kws)
logging.verbose = verbose

def ensure_dump_folder_exists():
    """Ensure the dump folder exists."""
    if not os.path.exists(DUMP_FOLDER):
        os.makedirs(DUMP_FOLDER)
        logging.info(f"Created '{DUMP_FOLDER}' directory.")

def download_media_file(url, base_url):
    """Download media file and maintain original folder structure."""
    if not url.startswith(('http://', 'https://')):
        url = urllib.parse.urljoin(base_url, url)
        relative_path = urllib.parse.urlparse(url).path
        if relative_path.startswith('/'):
            relative_path = relative_path[1:]
    else:
        relative_path = os.path.basename(urllib.parse.urlparse(url).path)
    
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            full_path = os.path.join(DUMP_FOLDER, relative_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
            logging.info(f"Downloaded media file: {full_path}")
            return relative_path
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
            
            relative_path = download_media_file(src, self.base_url)
            if relative_path:
                full_path = os.path.join(DUMP_FOLDER, relative_path)
                
                api_key = os.environ.get('OPENAI_API_KEY')
                prompt = "Describe this image in detail, focusing on what it shows and its context."
                image_description = describe_image(full_path, api_key, prompt)
                
                markdown_image = f'![{alt_text}]({DUMP_FOLDER}/{relative_path})\n'
                
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
        if el.get('download') is not None:
            href = el.get('href')
            if href and (href.endswith('.mp3') or href.endswith('.wav')):
                relative_path = download_media_file(href, self.base_url)
                if relative_path:
                    full_path = os.path.join(DUMP_FOLDER, relative_path)
                    
                    api_key = os.environ.get('OPENAI_API_KEY')
                    transcript = transcribe_audio(full_path, api_key)
                    
                    return f'\n\n[🔊 {text}]({DUMP_FOLDER}/{relative_path})\n\n**Transkrypcja pliku audio:** {transcript}\n\n'
        
        return super().convert_a(el, text, convert_as_inline)

    def convert_style(self, el, text, convert_as_inline):
        """Remove style elements by returning empty string."""
        return ''

def url_to_markdown(url):
    """Convert webpage at given URL to markdown format."""
    ensure_dump_folder_exists()
    
    response = requests.get(url)
    if response.status_code == 200:
        logging.info("Successfully fetched the web page.")
        
        # Create converter instance and set base_url
        converter = CustomMarkdownConverter(extras=['tables', 'fenced-code-blocks'])
        converter.base_url = url
        
        # Convert HTML to markdown
        markdown_text = converter.convert(response.text)
        
        # Generate unique filename based on URL
        parsed = urlparse(url)
        path = parsed.path.strip('/').replace('/', '_') or 'index'
        output_filename = f"{path}.md"
        
        # Save markdown content to file
        output_path = os.path.join(DUMP_FOLDER, output_filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_text)
        
        logging.info(f"Saved markdown content to {output_path}")
        return markdown_text
    else:
        logging.error(f"Failed to fetch the web page. Status code: {response.status_code}")
        return None

@dataclass
class PageState:
    url: str
    markdown_file: str
    parent_url: Optional[str] = None

class WebsiteExplorer:
    def __init__(self, base_url: str, dump_folder: str):
        self.base_url = base_url
        self.dump_folder = dump_folder
        self.visited_urls: List[str] = []
        self.page_stack: List[PageState] = []
        self.client = OpenAI()

    def get_markdown_filename(self, url: str) -> str:
        """Generate a unique markdown filename for the URL"""
        parsed = urlparse(url)
        path = parsed.path.strip('/').replace('/', '_') or 'index'
        return f"{path}.md"

    def explore(self, question: str) -> Optional[str]:
        """Main exploration loop to find answer to question"""
        current_url = self.base_url
        
        while True:
            # Convert current page to markdown
            current_state = PageState(
                url=current_url,
                markdown_file=self.get_markdown_filename(current_url)
            )
            
            markdown_content = url_to_markdown(current_url)
            if not markdown_content:
                return None

            # Prepare visited URLs for prompt
            visited_str = ", ".join(self.visited_urls)
            
            # Query AI for next action
            prompt = """Please act as my internet research assistant.

I will provide you with:

QUESTION: A question I need answered.
PAGE: An internet page in markdown format to be checked.
VISITED: A list of already checked URLs that should not be suggested again.

Your tasks:

Read the text from the PAGE section.

Based on the content, perform one of the following actions:

Answer the question if the answer is found within the PAGE.

Suggest the most likely next HTTP address to check based on the links in the PAGE. When suggesting a next address:

Do not give up as long as there are unvisited links on the page.

Select links based on the likelihood that the answer to the question is found behind the link.

Use the URL from the markdown links (the text inside the parentheses ( )), not the link descriptions.

Ensure the suggested URL is not in the VISITED list.

Indicate to go back only if there are no unvisited links on the page or there are no valid suggestions.

Response Format:

Please respond in the following JSON structure WITHOUT ANY FORMATTING OR ADDITIONAL COMMENTS. Do not add any formatting like ```json``` or other comments. Return only the raw JSON:
{
  "action": "found" | "search" | "back",
  "answer": "Answer to the question" | "Valid HTTP address to check in the next step" | "none"
}

Additional Notes:

When analyzing the next possible address to suggest:

Use the link descriptions (the text inside the brackets [ ]) in the markdown text to determine which links are most likely to contain the answer.

Prioritize links that are more likely to lead to the answer based on their descriptions.

Continue suggesting unvisited links until all have been checked before choosing to "back".

Do not suggest any URLs that are listed in the VISITED field."""

            response = text_chat(
                f"QUESTION: {question}\nVISITED: {visited_str}\nPAGE: {markdown_content}",
                self.client,
                args=args,
                prompt=prompt
            )

            try:
                result = json.loads(response)
                
                if result["action"] == "found":
                    return result["answer"]
                
                elif result["action"] == "search":
                    next_url = result["answer"]
                    if not next_url.startswith(('http://', 'https://')):
                        next_url = urljoin(current_url, next_url)
                    
                    self.visited_urls.append(current_url)
                    self.page_stack.append(current_state)
                    current_url = next_url
                
                elif result["action"] == "back":
                    if not self.page_stack:
                        # We're at the main page and can't go back
                        return None
                    
                    current_state = self.page_stack.pop()
                    current_url = current_state.url
                
            except json.JSONDecodeError:
                logging.error("Failed to parse AI response as JSON")
                return None

# Set up argument parser
parser = argparse.ArgumentParser(description='AI Devs API script for web crawling and question answering')
parser.add_argument('--debug', choices=['debug', 'info', 'verbose', 'off'], default='off', help='Debug mode')
parser.add_argument('--url', required=True, help='Starting URL for the web crawler')
parser.add_argument('--question', required=True, help='Question to be answered from the website content')

args = parser.parse_args()

def main():
    # Set up logging based on debug mode
    if args.debug == "debug":
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    elif args.debug == "info":
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    elif args.debug == "verbose":
        logging.basicConfig(level=VERBOSE_VALUE, format='%(asctime)s - %(levelname)s - %(message)s')
    else:
        logging.disable(sys.maxsize)

    explorer = WebsiteExplorer(
        base_url=args.url,
        dump_folder=DUMP_FOLDER
    )
    
    answer = explorer.explore(args.question)
    
    if answer:
        print(f"Answer found: {answer}")
    else:
        print("Could not find an answer to the question")

if __name__ == "__main__":
    main()