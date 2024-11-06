import requests
import sys
import os
import json
import logging
import argparse
import webbrowser
from bs4 import BeautifulSoup
from openai import OpenAI
from tempfile import NamedTemporaryFile

# Set up argument parser
parser = argparse.ArgumentParser(description='AI Devs API script')
parser.add_argument('--debug', choices=['debug', 'info', 'off'], default='off', help='Debug mode')
parser.add_argument('--url', help='URL to scrape')
parser.add_argument('--browser', choices=['yes', 'no'], default='no', help='Open response in browser')
args = parser.parse_args()

# Set up logging based on debug mode
if args.debug == "debug":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
elif args.debug == "info":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
else:
    logging.disable(sys.maxsize)

# Use the task name from command line arguments
KEY = os.environ.get("OPENAI_API_KEY")

# Scrape the webpage
logging.info(f"Scraping webpage: {args.url}")
response = requests.get(args.url)
soup = BeautifulSoup(response.text, 'html.parser')

# Find the captcha question
captcha_question = soup.find('p', {'id': 'human-question'}).text.replace('Question:', '').strip()
logging.info(f"Captcha question: {captcha_question}")

# Use OpenAI to answer the question
client = OpenAI(api_key=KEY)
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a helpful assistant. Always respond with only a year number (YYYY format). Do not include any other text or explanation in your response."},
        {"role": "user", "content": captcha_question}
    ],
    temperature=0,  # Set to 0 for most deterministic response
    max_tokens=10   # Reduced since we only need a year
)
captcha_answer = response.choices[0].message.content.strip()
logging.info(f"Captcha answer: {captcha_answer}")

# Login to the webpage
login_data = {
    'username': 'tester',
    'password': '574e112a',
    'answer': captcha_answer
}
logging.info(f"Logging in to webpage: {args.url}")
response = requests.post(args.url, data=login_data)

# Check if login was successful
if response.status_code == 200:
    logging.info("Login successful")
    
    if args.browser == 'yes':
        # Create a temporary HTML file and open it in the browser
        with NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(response.text)
            temp_path = f.name
        webbrowser.open('file://' + temp_path)
        logging.info(f"Opening response in browser from temporary file: {temp_path}")
    else:
        # Print the content of the page after login
        print(response.text)
else:
    logging.error(f"Login failed with status code: {response.status_code}")