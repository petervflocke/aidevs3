import requests
import sys
import os
import json
import logging
import argparse
from bs4 import BeautifulSoup
from openai import OpenAI
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

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

# Initialize Selenium webdriver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)
driver.get(args.url)

# Wait for the form to be available
wait = WebDriverWait(driver, 10)
username_field = wait.until(EC.presence_of_element_located((By.NAME, 'username')))
password_field = wait.until(EC.presence_of_element_located((By.NAME, 'password')))
answer_field = wait.until(EC.presence_of_element_located((By.NAME, 'answer')))

# Find and fill the login form
username_field.send_keys('tester')
password_field.send_keys('574e112a')
answer_field.send_keys(captcha_answer)

# Submit the form
answer_field.submit()

# Check if login was successful
if 'firmware' in driver.current_url:
    logging.info("Login successful")
    # Print the content of the page after login
    print(driver.page_source)
    print("Browser will remain open. Close it manually when done.")
    input("Press Enter to continue...")    
else:
    logging.error("Login failed")
    # Close the browser
    driver.quit()