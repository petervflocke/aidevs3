from fastapi import FastAPI
import uvicorn
from pydantic import BaseModel
import argparse
from openai import OpenAI
from text_classifier import text_chat
import json
import os
import logging
import sys

# Set up custom VERBOSE logging level
VERBOSE_VALUE = 15  # Between DEBUG (10) and INFO (20)
logging.addLevelName(VERBOSE_VALUE, "VERBOSE")
def verbose(message, *args, **kws):
    logging.log(VERBOSE_VALUE, message, *args, **kws)
logging.verbose = verbose

# Define 4x4 table structure
MAP = [
    ["start", "łąka",    "drzewo",  "domy"],
    ["łąka",  "wiatrak", "łąka",    "łąka"],
    ["łąka",  "łąka",    "skały",   "dwa drzewa"],
    ["góry", "góry",   "samochód", "jaskinia"]
]

# Define the prompt for AI
PROMPT = """
You are an expert interpreter for navigating a 4x4 grid map in a robot drone game. The map is represented as map[row][col], with [0][0] being the starting point at the top-left corner.

Your task is to analyze and interpret a human language description of movements starting from [0][0] and calculate the final position on the grid. The description may include irrelevant terms, canceled commands, or instructions to start over. Carefully process all instructions, but only consider the final decisions to determine the correct position on the grid.

Output format:
Return only the final position as a JSON object in the following format:
{  "row": <final_row>,  "col": <final_col> } 
Note: Only return the JSON coordinates, do not add any formatting like ```json``` or other comments.
"""

# Define the request model
class Instruction(BaseModel):
    instruction: str

# Create FastAPI instance
app = FastAPI()

@app.post("/drone")
def handle_instruction(instruction_data: Instruction):
    print(f"\nReceived instruction: {instruction_data.instruction}")
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        
        # Create args object for text_chat function
        class Args:
            debug = "verbose"  # Set to verbose to see detailed logging
        args = Args()
        
        # Get coordinates from AI
        print("\nSending to ChatGPT for interpretation...")
        response = text_chat(instruction_data.instruction, client, args, PROMPT)
        print(f"Raw ChatGPT response: {response}")
        
        # Parse the JSON response
        coords = json.loads(response)
        row = coords['row']
        col = coords['col']
        print(f"Parsed coordinates: row={row}, col={col}")
        
        # Validate coordinates
        if 0 <= row <= 3 and 0 <= col <= 3:
            value = MAP[row][col]
            print(f"Found value at coordinates: {value}")
            return {"description": value}
        else:
            print(f"Invalid coordinates: row={row}, col={col}")
            return {"error": "Invalid coordinates returned by AI"}
            
    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    # Set up command line argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    parser.add_argument("--debug", choices=['debug', 'info', 'verbose', 'off'], 
                       default='verbose', help='Debug mode')
    args = parser.parse_args()
    
    # Set up logging based on debug argument
    if args.debug == "debug":
        logging.basicConfig(level=logging.DEBUG, 
                          format='%(asctime)s - %(levelname)s - %(message)s')
    elif args.debug == "info":
        logging.basicConfig(level=logging.INFO, 
                          format='%(asctime)s - %(levelname)s - %(message)s')
    elif args.debug == "verbose":
        logging.basicConfig(level=VERBOSE_VALUE, 
                          format='%(asctime)s - %(levelname)s - %(message)s')
    else:
        logging.disable(sys.maxsize)
    
    # Run the server
    uvicorn.run(app, host="0.0.0.0", port=args.port)
