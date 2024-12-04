import os
import logging
import json
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from openai import OpenAI
import argparse
import time
import asyncio
import aiohttp

# Constants
TOKEN_ENDPOINT = "https://rafal.ag3nts.org/b46c3"
PASSWORD = "NONOMNISMORIAR"
DUMP_FOLDER = "S05E03"
RESULTS_FILE = "results.txt"
INPUT_FILE = "content.md"

# API key setup
KEYDEVS = os.environ.get('AIDEVS')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
if not KEYDEVS or not OPENAI_API_KEY:
    raise ValueError("AIDEVS and OPENAI_API_KEY environment variables must be set")

class QuestionsAgent:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.content = self._read_content_file()
        self._setup_logging()

    def _setup_logging(self):
        """Setup logging to file with timestamps"""
        try:
            # Ensure the dump folder exists
            os.makedirs(DUMP_FOLDER, exist_ok=True)
            
            # Remove existing log file if it exists
            results_path = os.path.join(DUMP_FOLDER, RESULTS_FILE)
            if os.path.exists(results_path):
                os.remove(results_path)
            
            # Reset logging configuration
            logging.getLogger().handlers = []
            
            # Create file handler
            file_handler = logging.FileHandler(
                filename=results_path,
                mode='a',  # append mode for single session
                encoding='utf-8'
            )
            
            # Create formatter
            formatter = logging.Formatter('%(asctime)s - %(message)s')
            file_handler.setFormatter(formatter)
            
            # Get logger and add handler
            logger = logging.getLogger()
            logger.setLevel(logging.INFO)
            logger.addHandler(file_handler)
            
            # Force immediate flush
            file_handler.flush()

        except Exception as e:
            print(f"Logging setup error: {str(e)}")
            raise

    def _read_content_file(self) -> str:
        """Read content from INPUT_FILE"""
        try:
            file_path = os.path.join(DUMP_FOLDER, INPUT_FILE)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Log first 200 characters of the content
                self._log_interaction("content_preview", {"first_200_chars": content[:200]})
                return content
        except Exception as e:
            logging.error(f"Error reading content file: {e}")
            return ""

    def _log_interaction(self, type_: str, data: Any):
        """Log interactions to RESULTS_FILE"""
        try:
            timestamp = datetime.now().isoformat()
            log_entry = {
                "timestamp": timestamp,
                "type": type_,
                "data": data
            }
            logging.info(json.dumps(log_entry, ensure_ascii=False))
            # Force immediate flush on all handlers
            for handler in logging.getLogger().handlers:
                handler.flush()
        except Exception as e:
            print(f"Logging error: {e}")
            raise

    def get_token(self) -> tuple[str, str, int]:
        """Get token and signature from TOKEN_ENDPOINT"""
        # First request to get the token
        payload = {"password": PASSWORD}
        response = requests.post(TOKEN_ENDPOINT, json=payload)
        self._log_interaction("token_request", {"payload": payload, "response": response.json()})
        
        if response.status_code != 200:
            raise ValueError(f"Failed to get token: {response.text}")
        
        token = response.json()["message"]
        
        # Second request to get signature
        payload = {"sign": token}
        response = requests.post(TOKEN_ENDPOINT, json=payload)
        self._log_interaction("signature_request", {"payload": payload, "response": response.json()})
        
        if response.status_code != 200:
            raise ValueError(f"Failed to get signature: {response.text}")
        
        data = response.json()["message"]
        return data["signature"], data["challenges"], data["timestamp"]

    async def fetch_single_source(self, session: aiohttp.ClientSession, url: str) -> Dict:
        """Fetch data from a single source URL"""
        async with session.post(url) as response:
            data = await response.json()
            self._log_interaction("source_fetch", {"url": url, "response": data})
            return data

    async def fetch_all_sources(self, urls: List[str]) -> List[Dict]:
        """Fetch data from all source URLs in parallel"""
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_single_source(session, url) for url in urls]
            return await asyncio.gather(*tasks)

    async def process_source_async(self, source: Dict) -> List[str]:
        """Process a single source asynchronously"""
        if source["task"] == "Odpowiedz na pytania":
            return await self.process_source0_async(source["data"])
        elif "arxiv-draft.html" in source["task"]:
            return await self.process_source1_async(source["data"])
        return []

    async def process_source0_async(self, questions: List[str]) -> List[str]:
        """Async version of process_source0"""
        prompt = """Answers below questions.
        Rules:
        - Answer ONLY in Polish language
        - Provide concise answers, preferably single word or date
        - Return answers as a JSON array of strings
        - Do not include any formatting symbols like ```json```
        
        Example format:
        {"response": ["answer1", "answer2", "answer3"]}
        
        Questions:
        {questions}"""
        
        formatted_questions = "\n".join(questions)
        response = await self.text_chat_async(formatted_questions, prompt)
        self._log_interaction("openai_source0", {"questions": questions, "response": response})
        
        response_data = json.loads(response)
        return response_data["response"]

    async def process_source1_async(self, questions: List[str]) -> List[str]:
        """Async version of process_source1"""
        prompt = """Answers below questions based on provided content.
        Source text:
        {content}
        
        Rules:
        - Answer ONLY in Polish language
        - Use only information from the provided source text
        - Provide extremely concise answers, preferably single word or phrase
        - Return answers as a JSON array of strings
        - Do not include any formatting symbols like ```json```
        
        Example format:
        {{"response": ["answer1", "answer2"]}}
        
        Questions:
        {questions}"""
        
        formatted_questions = "\n".join(questions)
        formatted_prompt = prompt.format(
            content=self.content,
            questions=formatted_questions
        )
        response = await self.text_chat_async(formatted_questions, formatted_prompt)
        self._log_interaction("openai_source1", {"questions": questions, "response": response})
        
        response_data = json.loads(response)
        return response_data["response"]

    async def text_chat_async(self, text: str, prompt: str) -> str:
        """Async version of text_chat"""
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": text}
        ]
        
        full_prompt = prompt + "\n" + text
        self._log_interaction("prompt_preview", {
            "first_200_chars": full_prompt[:200],
            "last_200_chars": full_prompt[-200:]
        })
        
        # OpenAI's client doesn't support async directly, but we can run it in a thread pool
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.1
            )
        )
        return response.choices[0].message.content.strip()

    async def process_all_sources(self, sources: List[Dict]) -> List[str]:
        """Process all sources in parallel"""
        tasks = [self.process_source_async(source) for source in sources]
        results = await asyncio.gather(*tasks)
        return [answer for sublist in results for answer in sublist]

    def submit_answers(self, answers: List[str], signature: str, timestamp: int) -> Dict:
        """Submit answers to TOKEN_ENDPOINT"""
        payload = {
            "apikey": KEYDEVS,
            "timestamp": timestamp,
            "signature": signature,
            "answer": answers
        }
        
        response = requests.post(TOKEN_ENDPOINT, json=payload)
        self._log_interaction("submit_answers", {"payload": payload, "response": response.json()})
        
        return response.json()

    async def process_single_source_complete(self, url: str) -> Tuple[List[str], float, float]:
        """Process a single source from fetch through AI processing"""
        fetch_start = time.perf_counter()
        async with aiohttp.ClientSession() as session:
            # Fetch data for this source
            source_data = await self.fetch_single_source(session, url)
            fetch_time = time.perf_counter() - fetch_start
            
            # Process the fetched data immediately
            process_start = time.perf_counter()
            if source_data["task"] == "Odpowiedz na pytania":
                answers = await self.process_source0_async(source_data["data"])
            elif "arxiv-draft.html" in source_data["task"]:
                answers = await self.process_source1_async(source_data["data"])
            else:
                answers = []
            process_time = time.perf_counter() - process_start
            
            return answers, fetch_time, process_time

    async def process_all_sources_parallel(self, challenges: List[str]) -> List[str]:
        """Create parallel tasks for complete processing of each source"""
        # Create a task for each challenge that includes both fetch and process
        tasks = [self.process_single_source_complete(url) for url in challenges]
        
        # Run all tasks in parallel and wait for completion
        results = await asyncio.gather(*tasks)
        
        # Print timing for each source
        for i, (answers, fetch_time, process_time) in enumerate(results, 1):
            print(f"\n   Source {i}:")
            print(f"   - Fetch time: {fetch_time:.3f} seconds")
            print(f"   - Process time: {process_time:.3f} seconds")
            print(f"   - Total time: {(fetch_time + process_time):.3f} seconds")
        
        # Return just the answers
        return [answer for answers, _, _ in results for answer in answers]

async def async_main(test_mode: bool = False):
    print("\n1. Initializing QuestionsAgent...")
    init_start = time.perf_counter()
    agent = QuestionsAgent()
    init_time = time.perf_counter() - init_start
    print(f"   Initialization time: {init_time:.3f} seconds")

    try:
        print("\n2. Getting token and signature...")
        token_start = time.perf_counter()
        signature, challenges, timestamp = agent.get_token()
        token_time = time.perf_counter() - token_start
        print(f"   Token acquisition time: {token_time:.3f} seconds")
        
        print("\n3. Processing sources in parallel (fetch + AI)...")
        process_start = time.perf_counter()
        all_answers = await agent.process_all_sources_parallel(challenges)
        process_time = time.perf_counter() - process_start
        print(f"   Total parallel processing time: {process_time:.3f} seconds")
        
        total_time = time.perf_counter() - init_start
        print(f"\n4. Final answers (total execution time: {total_time:.3f} seconds):")
        print(json.dumps(all_answers, indent=2, ensure_ascii=False))
        
        if not test_mode:
            print("\n5. Submitting answers to endpoint...")
            submit_start = time.perf_counter()
            result = agent.submit_answers(all_answers, signature, timestamp)
            submit_time = time.perf_counter() - submit_start
            print(f"   Submission time: {submit_time:.3f} seconds")
            print("\n6. Final result:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("\nTest mode: Skipping submission to endpoint")
        
    except Exception as e:
        logging.error(f"Error in main execution: {e}")
        raise

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='Run in test mode without submitting answers')
    args = parser.parse_args()
    
    asyncio.run(async_main(args.test))

if __name__ == "__main__":
    main()
