import logging
import requests
import os

# Function to transcribe audio file
def transcribe_audio(file_path, api_key):
    with open(file_path, "rb") as audio_file:
        logging.debug("Sending audio file to OpenAI for transcription")
        files = {
            "file": (os.path.basename(file_path), audio_file, "audio/mpeg")
        }
        data = {
            "model": "whisper-1"
        }
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        audio_response = requests.post("https://api.openai.com/v1/audio/transcriptions", headers=headers, files=files, data=data)
        logging.debug("Response from API: %s", audio_response.text)
        try:
            transcript = audio_response.json()["text"]
        except KeyError:
            logging.error("Error: 'text' key not found in API response")
            transcript = ""
    return transcript
