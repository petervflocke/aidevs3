import os
import logging
import json
import requests
from typing import Dict, Optional, Any
from openai import OpenAI
from datetime import datetime

# Constants
PLACES_API_ENDPOINT = "https://centrala.ag3nts.org/places"
SQL_API_ENDPOINT = "https://centrala.ag3nts.org/apidb"
GPS_API_ENDPOINT = "https://centrala.ag3nts.org/gps"
QUESTION_API_ENDPOINT = "https://centrala.ag3nts.org/data/{}/gps_question.json"
DUMP_FOLDER = "S05E02"
RESULTS_FILE = "results.txt"

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
        os.makedirs(DUMP_FOLDER, exist_ok=True)
        self.results_file = open(os.path.join(DUMP_FOLDER, RESULTS_FILE), 'w', encoding='utf-8')
        self.system_prompt = """You are an AI agent tasked with helping locate people using various APIs.
You have access to these tools:

1. places_api(location): Query places API to get information about who was seen at a specific location
   - Input: location name (string)
   - Output: List of people seen at that location
   - Example: places_api("LUBAWA") -> Returns people seen in Lubawa

2. sql_query(query): Query SQL database to get user information
   - Input: SQL query (string)
   - Output: User data (id, username, etc.)
   - Example: sql_query("SELECT id, username FROM users WHERE username='John'")
   - Note: Never query information about "Barbara"

3. gps_data(user_id): Get GPS coordinates for a user
   - Input: user_id (string)
   - Output: GPS coordinates {lat, lon}
   - Example: gps_data("123") -> Returns user's coordinates

For each step, tell me:
1. Which tool you want to use
2. The exact parameters to use
3. Your reasoning for this choice

Respond in JSON format like this:
{
    "tool": "tool_name",
    "parameters": "exact_parameters",
    "reasoning": "your reasoning"
}

If you have all needed information, respond with:
{
    "final_result": true,
    "coordinates": {
        "person_name": {"lat": value, "lon": value},
        ...
    }
}"""

    def log_interaction(self, step: str, sent: str, received: Any) -> None:
        """Log interactions to the results file"""
        timestamp = datetime.now().isoformat()
        self.results_file.write(f"\n{'='*50}\n")
        self.results_file.write(f"Step: {step} - {timestamp}\n")
        self.results_file.write(f"Sent:\n{sent}\n")
        self.results_file.write(f"Received:\n{json.dumps(received, indent=2, ensure_ascii=False) if isinstance(received, (dict, list)) else str(received)}\n")
        self.results_file.write(f"{'='*50}\n")
        self.results_file.flush()  # Force write to disk

    def text_chat(self, text: str, prompt: str = None) -> str:
        """Simplified version of text_chat for agent communication"""
        messages = [
            {"role": "system", "content": prompt or self.system_prompt},
            {"role": "user", "content": text}
        ]
        
        self.log_interaction("OpenAI Request", json.dumps(messages, indent=2), None)
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.1
        )
        result = response.choices[0].message.content.strip()
        
        self.log_interaction("OpenAI Response", None, result)
        return result

    def get_data_from_api(self, endpoint: str, query: str) -> Optional[Dict]:
        """Tool: Get data from API endpoint"""
        self.log_interaction(f"API Request to {endpoint}", query, None)
        
        headers = {'Content-Type': 'application/json'}
        data = {'apikey': KEYDEVS, 'query': query}
        response = requests.post(endpoint, json=data, headers=headers)
        result = response.json() if response.status_code == 200 else None
        
        self.log_interaction(f"API Response from {endpoint}", None, result)
        return result

    def send_sql_query(self, query: str) -> Dict[str, Any]:
        """Tool: Send SQL query to the API endpoint"""
        if 'barbara' in query.lower():
            raise ValueError("Security Alert: Attempting to query restricted information")
        
        self.log_interaction("SQL Query", query, None)
            
        payload = {
            "task": "database",
            "apikey": KEYDEVS,
            "query": query
        }
        response = requests.post(SQL_API_ENDPOINT, json=payload)
        response.raise_for_status()
        result = response.json()
        
        self.log_interaction("SQL Response", None, result)
        return result

    def get_gps_data(self, user_id: str) -> Optional[Dict[str, float]]:
        """Tool: Get GPS data for a user ID"""
        self.log_interaction("GPS Request", user_id, None)
        
        payload = {"userID": user_id}
        response = requests.post(GPS_API_ENDPOINT, json=payload)
        
        result = None
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 0 and 'message' in data:
                result = data['message']
                
        self.log_interaction("GPS Response", None, result)
        return result

    def get_question(self) -> str:
        """Get the task question from the API"""
        url = QUESTION_API_ENDPOINT.format(KEYDEVS)
        self.log_interaction("Question Request", url, None)
        
        response = requests.get(url)
        if response.status_code == 200:
            result = response.json()
            self.log_interaction("Question Response", None, result)
            return result.get('question')
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

    def execute_agent_action(self, action: Dict) -> Dict:
        """Execute a single action requested by the agent"""
        if 'final_result' in action:
            return action
            
        tool = action.get('tool')
        params = action.get('parameters')
        
        if tool == 'places_api':
            return self.get_data_from_api(PLACES_API_ENDPOINT, params)
        elif tool == 'sql_query':
            return self.send_sql_query(params)
        elif tool == 'gps_data':
            return self.get_gps_data(params)
        else:
            raise ValueError(f"Unknown tool: {tool}")

    def solve_task(self, question: str) -> Dict:
        """Main method to solve the task using agent-driven approach"""
        conversation = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Task: {question}\nWhat should we do first?"}
        ]
        
        while True:
            # Get next action from AI
            self.log_interaction("Agent Conversation", json.dumps(conversation, indent=2), None)
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=conversation,
                temperature=0.1
            )
            
            action_text = response.choices[0].message.content.strip()
            self.log_interaction("Agent Response", None, action_text)
            
            try:
                action = json.loads(action_text)
                
                # Check if we have final result
                if 'final_result' in action:
                    return action['coordinates']
                
                # Execute the requested action
                result = self.execute_agent_action(action)
                
                # Add the interaction to conversation
                conversation.append({"role": "assistant", "content": action_text})
                conversation.append({"role": "user", "content": f"Result: {json.dumps(result)}\nWhat should we do next?"})
                
            except Exception as e:
                error_msg = f"Error executing action: {str(e)}"
                self.log_interaction("Error", action_text, error_msg)
                conversation.append({"role": "user", "content": f"Error: {error_msg}. Please try a different approach."})

    def __del__(self):
        """Cleanup: Close the results file"""
        if hasattr(self, 'results_file'):
            self.results_file.close()

def main():
    agent = GPSAgent()
    try:
        # Get and analyze the task
        question = agent.get_question()
        
        # Let the agent solve it
        result = agent.solve_task(question)
        
        # Log and output results
        agent.log_interaction("Final Results", None, result)
        print(json.dumps(result, indent=4))
        
    except Exception as e:
        logging.error(f"Error in main execution: {e}")
        if hasattr(agent, 'results_file'):
            agent.log_interaction("Error", None, str(e))
        raise
    finally:
        if hasattr(agent, 'results_file'):
            agent.results_file.close()

if __name__ == "__main__":
    main()
