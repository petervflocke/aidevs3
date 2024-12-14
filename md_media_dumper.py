"""
md_media_dumper.py

This script is designed to extract and download media files (images and videos) from markdown files. 
It processes markdown files to find media links, downloads the media, and updates the markdown files 
to reference the downloaded media locally.

Usage:
    python md_media_dumper.py <path>

    - <path>: The path to a markdown file or a directory containing markdown files. The script will 
      process all markdown files found in the specified directory and its subdirectories.

Features:
    - Extracts image links in the format ![alt](url) and video links embedded in iframes.
    - Downloads images and videos to a 'media' folder within the specified path.
    - Updates markdown files to reference the downloaded media using local paths.
    - Supports downloading Vimeo videos using yt-dlp.
    - Provides a summary of the processing, including the number of files processed, successful 
      downloads, and any errors encountered.

Dependencies:
    - requests: For downloading media files.
    - yt-dlp: For downloading videos from Vimeo.
    - argparse, os, re, logging, json, pathlib: Standard Python libraries for argument parsing, 
      file handling, regular expressions, logging, and path manipulations.

Logging:
    - Logs are printed to the console with timestamps and log levels for easy debugging and tracking 
      of the script's operations.

Example:
    To process a single markdown file:
        python md_media_dumper.py /path/to/markdown_file.md

    To process all markdown files in a directory:
        python md_media_dumper.py /path/to/directory

Author:
    [Your Name]

Date:
    [Date]

"""

import argparse
import os
import re
import requests
from pathlib import Path
from urllib.parse import urlparse
import logging
import json
import yt_dlp

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ProcessingSummary:
    def __init__(self):
        self.total_files = 0
        self.successful_files = 0
        self.failed_files = 0
        self.errors = []  # List of (file_path, error_message) tuples
        self.downloads = {
            'videos': {'success': 0, 'failed': 0},
            'images': {'success': 0, 'failed': 0}
        }
    
    def add_error(self, file_path, error_msg):
        self.errors.append((file_path, error_msg))
    
    def print_summary(self):
        logging.info("\n=== Processing Summary ===")
        logging.info(f"Total files processed: {self.total_files}")
        logging.info(f"Successfully processed: {self.successful_files}")
        logging.info(f"Failed to process: {self.failed_files}")
        logging.info(f"\nDownloads:")
        logging.info(f"Videos: {self.downloads['videos']['success']} successful, {self.downloads['videos']['failed']} failed")
        logging.info(f"Images: {self.downloads['images']['success']} successful, {self.downloads['images']['failed']} failed")
        
        if self.errors:
            logging.info("\nErrors encountered:")
            for file_path, error in self.errors:
                logging.error(f"{file_path}: {error}")

def parse_arguments():
    parser = argparse.ArgumentParser(description='Extract and download media from markdown files')
    parser.add_argument('path', help='Markdown file or folder containing markdown files')
    return parser.parse_args()

def find_markdown_files(path):
    """Find markdown file(s) from given path"""
    path = Path(path)
    if path.is_file() and path.suffix.lower() == '.md':
        markdown_files = [path]
        logging.info(f"Processing single file: {path}")
    else:
        markdown_files = list(Path(path).glob('**/*.md'))
        logging.info(f"Found {len(markdown_files)} markdown files in folder")
    return markdown_files

def create_media_folder(base_folder):
    """Create simple media folder if it doesn't exist"""
    media_folder = Path(base_folder) / 'media'
    media_folder.mkdir(exist_ok=True)
    return media_folder

def extract_media_links(content):
    """Extract both image and video links from markdown content"""
    # Image pattern: ![alt](url)
    image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    images = re.findall(image_pattern, content)
    
    # Video pattern (iframe src)
    video_pattern = r'<iframe[^>]*src="([^"]+)"[^>]*>'
    videos = re.findall(video_pattern, content)
    
    return images, videos

def extract_vimeo_info(url):
    """Extract video ID and hash from Vimeo iframe src"""
    pattern = r'player\.vimeo\.com/video/(\d+)\?h=([a-zA-Z0-9]+)'
    match = re.search(pattern, url)
    if match:
        video_id = match.group(1)
        video_hash = match.group(2)
        return f"https://player.vimeo.com/video/{video_id}?h={video_hash}", f"{video_id}-{video_hash}"
    return None, None

def download_media_file(url, media_folder):
    """Download media file and return local path using flat structure"""
    try:
        parsed_url = urlparse(url)
        # Create flattened filename by replacing '/' with '_'
        flat_filename = f"{parsed_url.netloc}{parsed_url.path}".replace('/', '_')
        local_path = media_folder / flat_filename
        
        if not local_path.exists():
            logging.info(f"Downloading: {url}")
            response = requests.get(url)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                f.write(response.content)
            logging.info(f"Saved to: {local_path}")
        else:
            logging.info(f"File already exists: {local_path}")
            
        return local_path
    except Exception as e:
        logging.error(f"Error downloading {url}: {str(e)}")
        return None

def check_media_exists(media_folder, filename):
    """Check if media file already exists"""
    media_path = Path(media_folder) / filename
    return media_path.exists()

def download_vimeo_video(video_url, media_folder, filename):
    """Download Vimeo video using yt-dlp if it doesn't exist"""
    video_path = Path(media_folder) / f"{filename}.mp4"
    
    if video_path.exists():
        logging.info(f"Video already exists: {video_path}")
        return True
        
    options = {
        'outtmpl': f'{media_folder}/{filename}.%(ext)s',
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
    }
    
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            logging.info(f"Downloading video: {video_url}")
            ydl.download([video_url])
            logging.info("Download complete!")
            return True
    except Exception as e:
        logging.error(f"Error downloading video: {str(e)}")
        return False

def update_markdown_content(content, media_folder, summary, file_path):
    """Update markdown content with local media links"""
    content_modified = False
    
    # First check for any Vimeo URLs in the content
    vimeo_url_pattern = r'player\.vimeo\.com/video/(\d+)\?h=([a-zA-Z0-9]+)'
    vimeo_matches = list(re.finditer(vimeo_url_pattern, content))
    
    if vimeo_matches:
        logging.info(f"Found {len(vimeo_matches)} Vimeo URLs in content")
        
        # Find and process complete iframe tags
        iframe_pattern = r'<div[^>]*><iframe[^>]*src="https://player\.vimeo\.com/video/(\d+)\?h=([a-zA-Z0-9]+)[^"]*"[^>]*></iframe></div><script[^>]*></script>'
        iframe_matches = list(re.finditer(iframe_pattern, content))
        
        # Process the found iframes
        for match in iframe_matches:
            video_id = match.group(1)
            video_hash = match.group(2)
            vimeo_url = f"https://player.vimeo.com/video/{video_id}?h={video_hash}"
            vimeo_filename = f"{video_id}-{video_hash}"
            
            # Check if video already exists
            if check_media_exists(media_folder, f"{vimeo_filename}.mp4"):
                logging.info(f"Video already exists, updating markdown only: {vimeo_filename}.mp4")
                success = True
            else:
                logging.info(f"Processing Vimeo video: {vimeo_url}")
                success = download_vimeo_video(vimeo_url, media_folder, vimeo_filename)
            
            if success:
                summary.downloads['videos']['success'] += 1
                new_content = content.replace(
                    match.group(0),
                    f"![[media/{vimeo_filename}.mp4]]"
                )
                
                # Verify replacement
                if new_content == content:
                    summary.add_error(file_path, f"Failed to replace iframe for video: {vimeo_url}")
                else:
                    content = new_content
                    content_modified = True
                    logging.info(f"Successfully replaced iframe with local video link: {vimeo_filename}.mp4")
            else:
                summary.downloads['videos']['failed'] += 1
                summary.add_error(file_path, f"Failed to process video: {vimeo_url}")
    
    # Handle image links
    image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    for match in re.finditer(image_pattern, content):
        alt_text, image_url = match.groups()
        if image_url.startswith(('http://', 'https://')):
            logging.info(f"Found remote image: {image_url}")
            try:
                local_path = download_media_file(image_url, media_folder)
                if local_path:
                    summary.downloads['images']['success'] += 1
                    relative_path = os.path.relpath(local_path, media_folder.parent)
                    new_content = content.replace(
                        f'![{alt_text}]({image_url})',
                        f'![{alt_text}]({relative_path})'
                    )
                    if new_content != content:
                        content = new_content
                        content_modified = True
                else:
                    summary.downloads['images']['failed'] += 1
                    summary.add_error(file_path, f"Failed to download image: {image_url}")
            except Exception as e:
                summary.downloads['images']['failed'] += 1
                summary.add_error(file_path, f"Error processing image {image_url}: {str(e)}")
    
    return content, content_modified

def main():
    args = parse_arguments()
    path = Path(args.path)
    
    if not path.exists():
        logging.error(f"Path {path} does not exist")
        return
    
    summary = ProcessingSummary()
    
    try:
        base_folder = path.parent if path.is_file() else path
        media_folder = create_media_folder(base_folder)
        
        markdown_files = find_markdown_files(path)
        summary.total_files = len(markdown_files)
        
        for md_file in markdown_files:
            logging.info(f"Processing: {md_file}")
            
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                updated_content, was_modified = update_markdown_content(content, media_folder, summary, md_file)
                
                if was_modified:
                    with open(md_file, 'w', encoding='utf-8') as f:
                        f.write(updated_content)
                    summary.successful_files += 1
                    logging.info(f"Content modified, updated file: {md_file}")
                else:
                    summary.successful_files += 1
                    logging.info(f"No changes needed for: {md_file}")
                    
            except Exception as e:
                summary.failed_files += 1
                summary.add_error(md_file, f"Failed to process file: {str(e)}")
                logging.error(f"Error processing {md_file}: {str(e)}")
                continue  # Continue with next file
                
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
    finally:
        summary.print_summary()

if __name__ == '__main__':
    main() 