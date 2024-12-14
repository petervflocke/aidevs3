import argparse
import os
import re
import requests
from pathlib import Path
from urllib.parse import urlparse
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def parse_arguments():
    parser = argparse.ArgumentParser(description='Extract and download media from markdown files')
    parser.add_argument('folder', help='Folder containing markdown files')
    return parser.parse_args()

def find_markdown_files(folder):
    """Find all markdown files in the given folder"""
    markdown_files = list(Path(folder).glob('**/*.md'))
    logging.info(f"Found {len(markdown_files)} markdown files")
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

def update_markdown_content(content, media_folder):
    """Update markdown content with local media links"""
    images, videos = extract_media_links(content)
    
    # Update image links
    for alt_text, url in images:
        if url.startswith(('http://', 'https://')):
            local_path = download_media_file(url, media_folder)
            if local_path:
                relative_path = os.path.relpath(local_path, media_folder.parent)
                content = content.replace(
                    f'![{alt_text}]({url})',
                    f'![{alt_text}]({relative_path})'
                )
    
    # Update video embeds
    for url in videos:
        if url.startswith(('http://', 'https://')):
            local_path = download_media_file(url, media_folder)
            if local_path:
                relative_path = os.path.relpath(local_path, media_folder.parent)
                content = content.replace(url, relative_path)
    
    return content

def main():
    args = parse_arguments()
    base_folder = Path(args.folder)
    
    if not base_folder.exists():
        logging.error(f"Folder {base_folder} does not exist")
        return
    
    media_folder = create_media_folder(base_folder)
    markdown_files = find_markdown_files(base_folder)
    
    for md_file in markdown_files:
        logging.info(f"Processing: {md_file}")
        
        # Read markdown content
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Update content with local media links
        updated_content = update_markdown_content(content, media_folder)
        
        # Write updated content back to file
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        logging.info(f"Updated: {md_file}")

if __name__ == '__main__':
    main() 