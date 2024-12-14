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

def download_vimeo_video(video_url, media_folder, filename):
    """Download Vimeo video using yt-dlp"""
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

def update_markdown_content(content, media_folder):
    """Update markdown content with local media links"""
    content_modified = False
    
    # Find iframe tags with Vimeo videos - updated pattern to match the full div+iframe+script
    iframe_pattern = r'<div[^>]*><iframe[^>]*src="https://player\.vimeo\.com/video/(\d+)\?h=([a-zA-Z0-9]+)[^"]*"[^>]*></iframe></div><script[^>]*></script>'
    
    for match in re.finditer(iframe_pattern, content):
        video_id = match.group(1)
        video_hash = match.group(2)
        vimeo_url = f"https://player.vimeo.com/video/{video_id}?h={video_hash}"
        vimeo_filename = f"{video_id}-{video_hash}"
        
        logging.info(f"Found Vimeo video: {vimeo_url}")
        
        # Download the video
        success = download_vimeo_video(vimeo_url, media_folder, vimeo_filename)
        
        if success:
            # Replace the entire div+iframe+script with Obsidian video embed
            new_content = content.replace(
                match.group(0),  # The entire match (div+iframe+script)
                f"![[media/{vimeo_filename}.mp4]]"
            )
            if new_content != content:
                content = new_content
                content_modified = True
                logging.info(f"Replaced Vimeo iframe with local video link: media/{vimeo_filename}.mp4")
    
    # Handle image links
    image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    for match in re.finditer(image_pattern, content):
        alt_text, image_url = match.groups()
        if image_url.startswith(('http://', 'https://')):
            logging.info(f"Found remote image: {image_url}")
            local_path = download_media_file(image_url, media_folder)
            if local_path:
                relative_path = os.path.relpath(local_path, media_folder.parent)
                new_content = content.replace(
                    f'![{alt_text}]({image_url})',
                    f'![{alt_text}]({relative_path})'
                )
                if new_content != content:
                    content = new_content
                    content_modified = True
                    logging.info(f"Replaced remote image with local link: {relative_path}")
    
    return content, content_modified

def main():
    args = parse_arguments()
    path = Path(args.path)
    
    if not path.exists():
        logging.error(f"Path {path} does not exist")
        return
    
    # Create media folder in the same directory as the file/folder
    base_folder = path.parent if path.is_file() else path
    media_folder = create_media_folder(base_folder)
    
    markdown_files = find_markdown_files(path)
    
    for md_file in markdown_files:
        logging.info(f"Processing: {md_file}")
        
        # Read markdown content
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Update content with local media links
        updated_content, was_modified = update_markdown_content(content, media_folder)
        
        # Only write back if content was actually modified
        if was_modified:
            logging.info(f"Content modified, updating file: {md_file}")
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(updated_content)
        else:
            logging.info(f"No changes needed for: {md_file}")

if __name__ == '__main__':
    main() 