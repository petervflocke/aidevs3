import os
import json
import argparse
from openai import OpenAI

# Define the system prompt for OpenAI
SYSTEM_PROMPT = """
You are a helpful assistant.
Always answer the question directly without any additional text or explanation.
"""

# Set up argument parser
parser = argparse.ArgumentParser(description='AI Devs API script')
parser.add_argument('--file', required=True, help='File to correct')
args = parser.parse_args()

# Load the input file
with open(args.file, 'r') as f:
    data = json.load(f)

# Retain the original structure
corrected_data = {
    "apikey": data.get("apikey"),
    "description": data.get("description"),
    "copyright": data.get("copyright"),
    "test-data": []
}

# Iterate through the data and correct the calculations
for item in data['test-data']:
    question = item['question']
    answer = item.get('answer')
    test = item.get('test')

    # Correct the math calculation
    if answer is not None:
        try:
            result = eval(question)
            if result != answer:
                print(f"Correcting calculation: {question} = {result} (not {answer})")
                item['answer'] = result
        except Exception as e:
            print(f"Error evaluating calculation: {question} ({e})")

    # Use OpenAI to answer the test question
    if test:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        ai_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.strip()},
                {"role": "user", "content": test['q']}
            ],
            temperature=0,  # Set to 0 for most deterministic response
            max_tokens=100  # Adjust as needed
        )
        test['a'] = ai_response.choices[0].message.content.strip()

    corrected_data['test-data'].append(item)

# Save the corrected data to a new file
output_file = os.path.splitext(args.file)[0] + '.json'
with open(output_file, 'w') as f:
    json.dump(corrected_data, f, indent=2)

print(f"Corrected data saved to {output_file}")