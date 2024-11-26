import sys
import os
import logging
import argparse
import json
from openai import OpenAI
from text_classifier import text_chat
from aidev3_tasks import send_task
import requests
from tabulate import tabulate
import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
import re
from image_processor import describe_image

DUMP_FOLDER = "S04E01"  # Updated folder name
RESULTS_FILE = os.path.join(DUMP_FOLDER, "results.txt")

VERBOSE_VALUE = 15
logging.addLevelName(VERBOSE_VALUE, "VERBOSE")

def verbose(message, *args, **kws):
    logging.log(VERBOSE_VALUE, message, *args, **kws)
logging.verbose = verbose

# Set up argument parser
parser = argparse.ArgumentParser(description='AI Devs API script')
parser.add_argument('--debug', choices=['debug', 'info', 'verbose', 'off'], default='off', help='Debug mode')
parser.add_argument('--task', required=False, help='Task name')
parser.add_argument('--test', choices=['yes', 'no'], default='no', help='Test mode')
parser.add_argument('--start', type=int, choices=[1, 2, 3], default=2,
                    help='Start from step: 1-test tool, 2-TBD, 3-send results')
parser.add_argument('--params', required=False, help='Parameters')
parser.add_argument('--func', choices=['download', 'photos', 'check'], 
                   help='Function to test: download, photos, or check')
args = parser.parse_args()

# Set up logging based on debug mode
if args.debug == "debug":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
elif args.debug == "info":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
elif args.debug == "verbose":
    logging.basicConfig(level=VERBOSE_VALUE, format='%(asctime)s - %(levelname)s - %(message)s')
else:
    logging.disable(sys.maxsize)

# API Keys setup
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
KEYDEVS = os.environ.get('AIDEVS')
if not KEYDEVS:
    raise ValueError("AIDEVS API KEY cannot be empty, setup environment variable AIDEVS")
if not OPENAI_API_KEY:
    raise ValueError("Open AI API key cannot be empty, setup environment variable OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

def download_image(url: str, folder: str = DUMP_FOLDER) -> str:
    """
    Downloads an image from a URL and saves it to the specified folder.
    Returns the local file path of the saved image.
    
    Args:
        url: URL of the image to download
        folder: Local folder to save the image (defaults to DUMP_FOLDER)
    """
    try:
        # Create folder if it doesn't exist
        Path(folder).mkdir(parents=True, exist_ok=True)
        
        # Extract filename from URL or generate one if not present
        filename = url.split('/')[-1]
        if not filename or not any(filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']):
            filename = f"image_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        
        filepath = os.path.join(folder, filename)
        
        # Download and save the image
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        logging.info(f"Successfully downloaded image to {filepath}")
        return filepath
        
    except Exception as e:
        logging.error(f"Error downloading image from {url}: {str(e)}")
        raise

def send_command(command: str, task: str = "photos", test_mode: bool = False) -> tuple[int, str]:
    """
    Wrapper for send_task function specifically for the photos task.
    
    Args:
        command: Command to send (START, REPAIR, DARKEN, BRIGHTEN with filename)
        task: Task name (default: photos)
        test_mode: If True, prints the response
    
    Returns:
        tuple containing (code, message)
    """
    try:
        # Log what we're sending to the endpoint
        request_data = {
            "task": task,
            "apikey": KEYDEVS,
            "answer": command
        }
        log_to_results("Sending to report endpoint:", request_data)
        
        response = send_task(task, KEYDEVS, command)
        if response:
            code = response.get('code', -1)
            msg = response.get('message', 'No message')
            
            log_to_results("Response from report endpoint:", {
                "code": code,
                "message": msg
            })
            
            if test_mode:
                print(f"Response - Code: {code}, Message: {msg}")
            
            return code, msg
        return -1, "No response"
    except Exception as e:
        error_msg = str(e)
        log_to_results("Error sending command:", {
            "command": command,
            "error": error_msg
        })
        logging.error(f"Error sending command: {error_msg}")
        return -1, error_msg

@dataclass
class ImageInfo:
    filename: str
    original_url: str
    processed_urls: List[str] = None
    operations_tried: List[str] = None
    
    def __post_init__(self):
        self.processed_urls = self.processed_urls or []
        self.operations_tried = self.operations_tried or []

def setup_results_file():
    """
    Setup results file: create folder if needed and clear existing file
    """
    # Create folder if it doesn't exist
    Path(DUMP_FOLDER).mkdir(parents=True, exist_ok=True)
    
    # Clear existing file
    with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"=== New Session Started at {timestamp} ===\n")

def log_to_results(message: str, data: Any = None, flush: bool = True):
    """
    Log message and data to the results file with timestamp
    """
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(RESULTS_FILE, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*50}\n")
        f.write(f"{timestamp} - {message}\n")
        if data:
            if isinstance(data, dict):
                f.write(json.dumps(data, indent=2, ensure_ascii=False))
            else:
                f.write(str(data))
        f.write("\n")
        if flush:
            f.flush()

class PhotoAnalyzer:
    BASE_URL = "https://centrala.ag3nts.org/dane/barbara/"
    
    def __init__(self, client: OpenAI):
        self.client = client
        self.images: List[ImageInfo] = []
        
    def parse_initial_response(self, response_msg: str) -> List[ImageInfo]:
        """
        Use AI to extract image information and create proper endpoints
        """
        log_to_results("Initial response from server:", response_msg)
        
        system_prompt = """
        Extract image information from the message and return a JSON object.
        Expected format:
        {
            "image_list": [
                {
                    "filename": "IMG_559.PNG",
                    "url": "https://centrala.ag3nts.org/dane/barbara/IMG_559.PNG"
                },
                ...
            ],
            "base_info": "additional context if any"
        }
        Do not add any formatting like ```json``` or other comments.
        """
        log_to_results("System prompt for parsing:", system_prompt)
        
        user_prompt = f"Message to parse: {response_msg}"
        
        logging.debug(f"System prompt: {system_prompt}")
        logging.debug(f"User prompt: {user_prompt}")
        
        try:
            completion = self.client.chat.completions.create(
                model="gpt-4o",  # Using gpt-4o model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                # Removed response_format as it's not supported by gpt-4o
            )
            
            response_content = completion.choices[0].message.content
            log_to_results("AI parsing response:", response_content)
            
            # Clean up potential formatting
            response_content = response_content.replace('```json', '').replace('```', '').strip()
            
            result = json.loads(response_content)
            self.images = [
                ImageInfo(
                    filename=img['filename'],
                    original_url=img['url']
                ) for img in result['image_list']
            ]
            logging.info(f"Extracted {len(self.images)} images: {[img.filename for img in self.images]}")
            return self.images
            
        except Exception as e:
            logging.error(f"Failed to parse image information: {str(e)}")
            logging.debug(f"Original message: {response_msg}")
            raise ValueError(f"Failed to parse image information: {str(e)}")

    def analyze_image_needs(self, image_path: str) -> Dict:
        """
        Use AI to analyze image and decide what processing is needed
        """
        prompt = """
        Analyze this image and provide a JSON response with:
        {
            "quality_assessment": "description of image quality, for overexposed we need BRIGHTEN, for underexposed DARKEN, for all other distortions we must REPAIR, if the quality is fine the action is NONE",
            "recommended_operation": "NONE|REPAIR|DARKEN|BRIGHTEN",
            "description": "detailed description of visible person",
            "confidence": 0-100
        }
        Do not add any formatting like ```json``` or other comments.
        """
        log_to_results(f"\nAnalyzing image: {image_path}")
        log_to_results("Analysis prompt:", prompt)
        
        try:
            response_content = describe_image(image_path, OPENAI_API_KEY, prompt)
            log_to_results("AI analysis response:", response_content)
            
            # Clean up potential formatting
            response_content = response_content.replace('```json', '').replace('```', '').strip()
            
            return json.loads(response_content)
            
        except Exception as e:
            logging.error(f"Error analyzing image {image_path}: {str(e)}")
            raise

    def generate_description(self, image_path: str, hints: List[str] = None) -> str:
        """
        Generate final description for submission
        """
        prompt = """
        We test a system for picture recognition, are you able to describe what you see on attached picture? Please provide description in Polish.
        Focus on:
        1. Physical characteristics
        2. Clothing
        3. Distinguishing features
        """
        
        if hints:
            prompt += f"\nPlease specifically address these aspects: {', '.join(hints)}"
        
        log_to_results(f"\nGenerating description for: {image_path}")
        log_to_results("Description prompt:", prompt)
        log_to_results("Current hints:", hints)
        
        try:
            description = describe_image(image_path, OPENAI_API_KEY, prompt)
            log_to_results("Generated description:", description)
            return description
            
        except Exception as e:
            logging.error(f"Error generating description for {image_path}: {str(e)}")
            raise

    def check_flag_in_response(self, response: str) -> bool:
        """Check if response contains a flag"""
        return bool(re.search(r'FLG:', response))

    def extract_hints(self, response: str) -> List[str]:
        """Extract hints from response"""
        log_to_results("Extracting hints from response:", response)
        
        try:
            if isinstance(response, str):
                data = json.loads(response)
            else:
                data = response  # Already a dict
            
            hints = data.get('hints', [])
            log_to_results("Extracted hints:", hints)
            return hints
            
        except json.JSONDecodeError:
            log_to_results("Failed to parse JSON response, trying regex fallback")
            # Try regex if JSON parsing fails
            hint_match = re.search(r'hints\':\s*\[(.*?)\]', response)
            if hint_match:
                hints = [h.strip(' \'\"') for h in hint_match.group(1).split(',')]
                log_to_results("Extracted hints using regex:", hints)
                return hints
            
            log_to_results("No hints found in response")
            return []

def process_photos():
    analyzer = PhotoAnalyzer(client)
    hints = []
    
    # Start task and get initial response
    code, msg = send_command("START")
    log_to_results("START command response:", {"code": code, "message": msg})
    
    if code != 0:
        log_to_results("Failed to start task", {"error": msg})
        raise Exception(f"Failed to start task: {msg}")
    
    # Parse initial response and get image info
    images = analyzer.parse_initial_response(msg)
    
    for img in images:
        logging.info(f"Processing image: {img.filename}")
        # Download original image
        original_path = download_image(img.original_url)
        
        while True:
            # Analyze current image state
            analysis = analyzer.analyze_image_needs(original_path)
            logging.info(f"Analysis result: {analysis}")
            
            # If image is good enough, generate description
            if analysis['recommended_operation'] == "NONE" and analysis['confidence'] > 70:
                description = analyzer.generate_description(original_path, hints)
                logging.info(f"Generated description: {description}")
                code, response = send_command(description)
                
                if analyzer.check_flag_in_response(response):
                    logging.info("Found flag! Task completed.")
                    return True
                    
                if code == -346:  # Specific code for hint response
                    new_hints = analyzer.extract_hints(response)
                    if new_hints:
                        logging.info(f"New hints received: {new_hints}")
                        log_to_results("Adding new hints to existing ones:", {
                            "existing_hints": hints,
                            "new_hints": new_hints
                        })
                        hints.extend(new_hints)
                        continue
                    
                break  # Try next image if no new hints
            
            # Apply recommended operation
            operation = analysis['recommended_operation']
            if operation not in img.operations_tried:
                logging.info(f"Applying operation {operation} to {img.filename}")
                code, msg = send_command(f"{operation} {img.filename}")
                if code == 0:
                    # Extract new filename and download processed image
                    processed_filename = re.search(r'IMG_\d+_F[A-Z0-9]+\.PNG', msg)
                    if processed_filename:
                        new_url = f"{PhotoAnalyzer.BASE_URL}{processed_filename.group()}"
                        img.processed_urls.append(new_url)
                        log_to_results("Downloading processed image:", {
                            "original_file": img.filename,
                            "processed_file": processed_filename.group(),
                            "url": new_url
                        })
                        original_path = download_image(new_url)  # Update path to new version
                        img.operations_tried.append(operation)
                        continue  # Continue with analysis of new version
            
            break  # Try next image if no more operations to try
    
    return False  # No solution found

def main():
    # Setup results file at the start
    setup_results_file()
    
    if args.start <= 1:
        if not args.func:
            logging.error("Function parameter (--func) is required for start=1")
            return
            
        if args.func == 'download':
            # Test the image download functionality
            if args.params:
                try:
                    test_url = args.params
                    saved_path = download_image(test_url)
                    logging.info(f"Test successful: Image saved to {saved_path}")
                except Exception as e:
                    logging.error(f"Test failed: {str(e)}")
                    
        elif args.func == 'photos':
            # Test the photos command wrapper
            if args.params:
                code, msg = send_command(args.params, test_mode=True)
                logging.info(f"Photos command test - Code: {code}, Message: {msg}")
                
        elif args.func == 'check':
            # Test specific task response
            if args.task and args.params:
                code, msg = send_command(args.params, task=args.task, test_mode=True)
                logging.info(f"Task check test - Code: {code}, Message: {msg}")
            else:
                logging.error("Both --task and --params are required for func=check")
    
    if args.start == 2:
        try:
            logging.info("Starting photo processing task...")
            log_to_results("Starting photo processing task")
            success = process_photos()
            if success:
                logging.info("Successfully completed the photo task!")
                log_to_results("Task completed successfully!")
            else:
                logging.error("Failed to complete the photo task - no flag found")
                log_to_results("Task failed - no flag found")
        except Exception as e:
            error_msg = str(e)
            if args.debug == "debug":
                import traceback
                error_msg = traceback.format_exc()
            logging.error(f"Error during photo processing: {error_msg}")
            log_to_results("Error during processing", error_msg)
    
    if args.start == 3 and args.test != 'yes':
        # TBD
        pass    

if __name__ == "__main__":
    main() 