import base64
import logging
import requests
import os

# Function to encode image
def encode_image(image_path):
    """Encodes an image file to a base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Function to describe image
def describe_image(image_path, api_key, prompt):
    """Encodes an image to base64 and sends it to OpenAI for description."""
    base64_image = encode_image(image_path)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ],
        "max_tokens": 300
    }

    image_response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    response_json = image_response.json()
    logging.debug("Response from API: %s", response_json["choices"][0]["message"]["content"])
    image_description = response_json["choices"][0]["message"]["content"]
    return image_description 