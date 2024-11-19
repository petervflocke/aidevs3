import logging
import json
from openai import OpenAI

# Function to send text to OpenAI for chat completion
def text_chat(text, client, args, prompt):
    logging.verbose("Sending text to OpenAI for chat: %s", text)

    if args.debug == "verbose":
        # Get the root logger
        root_logger = logging.getLogger()
        # Store the current logging level
        previous_logging_level = root_logger.level
        # Temporarily disable logging
        root_logger.setLevel(logging.CRITICAL)

    api_response = client.chat.completions.create(
        model="gpt-4o",
        #model="gpt-4o-mini",
        #model="gpt-3.5-turbo",
        #model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text}
        ]
    )
    # Restore the previous logging configuration
    if args.debug == "verbose":
        root_logger.setLevel(previous_logging_level)

    logging.debug("Response from API: %s", api_response.choices[0].message.content.strip())
    return api_response.choices[0].message.content.strip() 