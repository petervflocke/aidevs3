import logging
import requests
import os

AI_DEVS_ENDPOINT = "https://centrala.ag3nts.org/"

def send_task(task, api_key, output, url=AI_DEVS_ENDPOINT):
    """Send task data to the specified URL."""
    data = {
        "task": task,
        "apikey": api_key,
        "answer": output
    }
    logging.info("Data to send: %s", data)
    url = f"{url}/report"
    response = requests.post(url, json=data)
    try:
        json_response = response.json()
        logging.info("Response from server: %s", json_response)
        return json_response
    except ValueError:
        logging.error("Failed to parse JSON response")
        return None

def fetch_file(api_key, endpoint, url=AI_DEVS_ENDPOINT):
    """Fetch a file from the specified endpoint using the API key."""
    if not api_key:
        raise ValueError("API KEY cannot be empty, setup environment variable AIDEVS")

    file_url = f"{url}/data/{api_key}/{endpoint}"
    logging.info(f"Fetching file from: {file_url}")

    response = requests.get(file_url)
    if response.status_code == 200:
        file_content = response.text.splitlines()
        logging.info(f"File fetched successfully. Number of lines: {len(file_content)}")
        return file_content
    else:
        logging.error(f"Failed to fetch the file. Error: {response.status_code}")
        return None 