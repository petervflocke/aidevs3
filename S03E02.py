import sys
import os
import logging
import argparse
import json
from openai import OpenAI
from text_classifier import text_chat
from aidev3_tasks import send_task
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, OptimizersConfigDiff
from datetime import datetime

SEARCHED_TEXT = """
W raporcie, z którego dnia znajduje się wzmianka o kradzieży prototypu broni?
"""

SEARCHED_TEXT = """
Kiedy skradziono urządzenie?
"""

DUMP_FOLDER = "S03E02-dump"

# Test configuration
test_include = [
    "2024_01_08.txt",
    "2024_01_17.txt"
]



VERBOSE_VALUE = 15  # Choose a value between existing levels
logging.addLevelName(VERBOSE_VALUE, "VERBOSE")

def verbose(message, *args, **kws):
    logging.log(VERBOSE_VALUE, message, *args, **kws)
logging.verbose = verbose

# Set up argument parser
parser = argparse.ArgumentParser(description='AI Devs API script')
parser.add_argument('--debug', choices=['debug', 'info', 'verbose', 'off'], default='off', help='Debug mode')
parser.add_argument('--folder', required=True, help='Path to the first folder containing files')
parser.add_argument('--test', choices=['yes', 'no'], default='no', help='Test mode')
parser.add_argument('--start', type=int, choices=[0, 1, 2, 3], default=1, 
                    help='Start from step: 0-delete collection, 1-cleaning collection, 2-TBD, 3-TBD')
args = parser.parse_args()

# Set up logging based on debug mode
if args.debug == "debug":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
elif args.debug == "info":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
elif args.debug == "verbose":
    logging.basicConfig(level=VERBOSE_VALUE, format='%(asctime)s - %(levelname)s - %(message)s')
else:
    logging.disable(sys.maxsize)

# API Keys setup
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
KEYDEVS = os.environ.get('AIDEVS')
QDRANT_URL = os.environ.get("QDRANT_URL")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")

if not KEYDEVS:
    raise ValueError("AIDEVS API KEY cannot be empty, setup environment variable AIDEVS")
if not OPENAI_API_KEY:
    raise ValueError("Open AI API key cannot be empty, setup environment variable OPENAI_API_KEY")
if not QDRANT_URL:
    raise ValueError("QDRANT_URL cannot be empty, setup environment variable QDRANT_URL")
if not QDRANT_API_KEY:
    raise ValueError("QDRANT_API_KEY cannot be empty, setup environment variable QDRANT_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

COLLECTION = "aidevs3"

def setup_qdrant_client():
    """Initialize Qdrant client with cloud credentials"""
    return QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
    )

def recreate_collection(client: QdrantClient):
    """Delete existing collection if exists and create a new one"""
    # Delete if exists
    try:
        client.delete_collection(collection_name=COLLECTION)
        logging.info(f"Deleted existing collection: {COLLECTION}")
    except Exception as e:
        logging.debug(f"Collection deletion skipped: {e}")

    # Create new collection
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=models.VectorParams(
            size=1536,  # Updated to match ada-002 embedding size
            distance=Distance.COSINE
        ),
        optimizers_config=models.OptimizersConfigDiff(
            deleted_threshold=0.2,
            vacuum_min_vector_number=1000,
            default_segment_number=0,
            indexing_threshold=20000,
            flush_interval_sec=5,
        ),
        on_disk_payload=True
    )
    logging.info(f"Created new collection: {COLLECTION}")

def create_embedding(content: str) -> list[float]:
    """Create embedding using OpenAI API"""
    logging.debug(f"Creating embedding for content: {content[:200]}...")  # Show first 200 chars
    
    try:
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=content,
            encoding_format="float"
        )
        embedding = response.data[0].embedding
        logging.debug(f"Created embedding of size: {len(embedding)}")
        return embedding
        
    except Exception as e:
        logging.error(f"Error creating embedding: {e}")
        raise

def extract_date_from_filename(filename: str) -> datetime | None:
    """Extract date from filename in format YYYY_MM_DD.txt"""
    try:
        # Extract first part of filename that matches YYYY_MM_DD format
        date_str = os.path.splitext(filename)[0].split('_')[:3]  # Remove extension and take first three parts
        if len(date_str) >= 3:
            year = date_str[0]
            month = date_str[1]
            day = date_str[2]
            # Parse into datetime object
            logging.debug(f"Extracted date from filename {filename}: {year}_{month}_{day}")
            return datetime.strptime(f"{year}_{month}_{day}", "%Y_%m_%d")
    except Exception as e:
        logging.error(f"Failed to parse date from filename {filename}: {e}")
    return None

def process_files(folder_path: str, qdrant_client: QdrantClient):
    """Process all files in the given folder and add their embeddings to Qdrant"""
    if not os.path.exists(folder_path):
        raise ValueError(f"Folder path does not exist: {folder_path}")
    
    processed_count = 0
    for filename in os.listdir(folder_path):
        # Skip files not in test_include list when in test mode
        if args.test == 'yes' and filename not in test_include:
            logging.debug(f"Skipping {filename} - not in test include list")
            continue
            
        file_path = os.path.join(folder_path, filename)
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            # Create embedding using OpenAI API
            embedding = create_embedding(content)
            
            # Extract date from filename
            file_date = extract_date_from_filename(filename)
            logging.debug(f"Extracted date from filename {filename}: {file_date}")
            # Prepare payload with additional metadata
            payload = {
                "filename": filename,
                "content": content,
                "date": file_date.isoformat() if file_date else None # Store as ISO format string
            }
            
            # Add point to Qdrant
            qdrant_client.upsert(
                collection_name=COLLECTION,
                points=[
                    models.PointStruct(
                        id=processed_count,  # Using counter as ID
                        vector=embedding,
                        payload=payload
                    )
                ]
            )
            
            processed_count += 1
            logging.info(f"Processed file {filename} ({processed_count} total)")
            logging.debug(f"Added metadata: {payload}")
            
        except Exception as e:
            logging.error(f"Error processing file {filename}: {e}")
            continue
    
    logging.info(f"Finished processing {processed_count} files")
    return processed_count

def search_similar_content(qdrant_client: QdrantClient, search_text: str) -> dict:
    """Search for the most similar content using the provided text"""
    logging.info(f"Searching for: {search_text}")
    
    try:
        # Create embedding for search text
        search_embedding = create_embedding(search_text)
        
        # Search in Qdrant for single best match
        search_results = qdrant_client.search(
            collection_name=COLLECTION,
            query_vector=search_embedding,
            limit=1  # Get only the best match
        )
        
        if not search_results:
            logging.warning("No results found")
            return None
            
        # Get the best match
        best_match = search_results[0]
        result_data = {
            "filename": best_match.payload["filename"],
            "content": best_match.payload["content"],
            "date": best_match.payload["date"],
            "score": best_match.score
        }
        
        logging.debug(f"Best match (score {best_match.score}) found in file {best_match.payload['filename']}")
        return result_data
        
    except Exception as e:
        logging.error(f"Error during search: {e}")
        raise

def main():
    # Initialize Qdrant client
    qdrant_client = setup_qdrant_client()
    
    # Step 0: Delete and recreate collection
    if args.start == 0:
        logging.info("Starting Step 0: Recreating collection")
        recreate_collection(qdrant_client)
        
    # Step 1: Process files and create embeddings
    if args.start <= 1:
        logging.info("Starting Step 2: Processing files and creating embeddings")
        try:
            files_processed = process_files(args.folder, qdrant_client)
            logging.info(f"Successfully processed {files_processed} files")
        except Exception as e:
            logging.error(f"Error in step 2: {e}")
            return
        
    # Step 2: Search for similar content
    if args.start <= 2:
        logging.info("Starting Step 2: Searching for similar content")
        try:
            result = search_similar_content(qdrant_client, SEARCHED_TEXT)
            
            if result:
                print("\nSearch Result:")
                print(f"Score: {result['score']:.4f}")
                print(f"File: {result['filename']}")
                print(f"Date: {result['date']}")
                print(f"Content: {result['content']}")
            else:
                print("No matching content found")
        except Exception as e:
            logging.error(f"Error in step 3: {e}")
            return

if __name__ == "__main__":
    main()
