import os
import logging
import json
import requests
from typing import Dict, Optional, Any
from openai import OpenAI

# Constants
PLACES_API_ENDPOINT = "https://centrala.ag3nts.org/places"
SQL_API_ENDPOINT = "https://centrala.ag3nts.org/apidb"
GPS_API_ENDPOINT = "https://centrala.ag3nts.org/gps"
QUESTION_API_ENDPOINT = "https://centrala.ag3nts.org/data/{}/gps_question.json"

# API key setup
KEYDEVS = os.environ.get('AIDEVS')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
if not KEYDEVS:
    raise ValueError("AIDEVS API KEY cannot be empty, setup environment variable AIDEVS")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI API KEY cannot be empty, setup environment variable OPENAI_API_KEY")

class GPSAgent:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.system_prompt = """You are an AI agent tasked with helping locate people using various APIs.
You have access to these tools:
1. Query places API - to get information about locations
2. Query SQL database - to get user information
3. Get GPS coordinates - to track user locations

Important: Never attempt to query information about "Barbara" as this will trigger security alerts.

Analyze the task and plan your approach carefully."""

    def text_chat(self, text: str, prompt: str = None) -> str:
        """Simplified version of text_chat for agent communication"""
        messages = [
            {"role": "system", "content": prompt or self.system_prompt},
            {"role": "user", "content": text}
        ]
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.1
        )
        return response.choices[0].message.content.strip()

    def get_data_from_api(self, endpoint: str, query: str) -> Optional[Dict]:
        """Tool: Get data from API endpoint"""
        headers = {'Content-Type': 'application/json'}
        data = {'apikey': KEYDEVS, 'query': query}
        response = requests.post(endpoint, json=data, headers=headers)
        return response.json() if response.status_code == 200 else None

    def send_sql_query(self, query: str) -> Dict[str, Any]:
        """Tool: Send SQL query to the API endpoint"""
        if 'barbara' in query.lower():
            raise ValueError("Security Alert: Attempting to query restricted information")
            
        payload = {
            "task": "database",
            "apikey": KEYDEVS,
            "query": query
        }
        response = requests.post(SQL_API_ENDPOINT, json=payload)
        response.raise_for_status()
        return response.json()

    def get_gps_data(self, user_id: str) -> Optional[Dict[str, float]]:
        """Tool: Get GPS data for a user ID"""
        payload = {"userID": user_id}
        response = requests.post(GPS_API_ENDPOINT, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 0 and 'message' in data:
                return data['message']
        return None

    def get_question(self) -> str:
        """Get the task question from the API"""
        url = QUESTION_API_ENDPOINT.format(KEYDEVS)
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get('question')
        raise ValueError("Failed to get question from API")

    def analyze_task(self, question: str) -> Dict:
        """Have the AI analyze the task and create a plan"""
        planning_prompt = """Analyze the given task and create a plan to solve it.
Return your response as a JSON object with these keys:
- location: the target location to search
- actions: list of steps to take
- restrictions: any security considerations

Format your response as valid JSON only."""

        plan = self.text_chat(question, planning_prompt)
        return json.loads(plan)

    def execute_plan(self, plan: Dict) -> Dict[str, Dict[str, float]]:
        """Execute the planned actions and return results"""
        result = {}
        
        # Get initial location data
        places_response = self.get_data_from_api(PLACES_API_ENDPOINT, plan['location'])
        if not places_response or places_response.get('code') != 0:
            raise ValueError("Failed to get places data")

        # Process each person while respecting restrictions
        names = places_response['message'].split()
        for name in names:
            if 'barbara' in name.lower():
                continue  # Skip restricted name
                
            try:
                # Get user ID
                sql_query = f'SELECT id, username FROM users WHERE lower(username)=lower("{name}")'
                sql_response = self.send_sql_query(sql_query)
                
                if sql_response.get('error') == 'OK' and sql_response.get('reply'):
                    user_data = sql_response['reply'][0]
                    user_id = user_data['id']
                    proper_name = user_data['username']

                    # Get GPS data
                    gps_data = self.get_gps_data(user_id)
                    if gps_data:
                        result[proper_name] = {
                            'lat': gps_data['lat'],
                            'lon': gps_data['lon']
                        }
            except Exception as e:
                logging.error(f"Error processing {name}: {e}")
                continue

        return result

def main():
    agent = GPSAgent()
    try:
        # Get and analyze the task
        question = agent.get_question()
        plan = agent.analyze_task(question)
        
        # Execute the plan and get results
        result = agent.execute_plan(plan)
        
        # Output results
        print(json.dumps(result, indent=4))
        
    except Exception as e:
        logging.error(f"Error in main execution: {e}")
        raise

if __name__ == "__main__":
    main()
