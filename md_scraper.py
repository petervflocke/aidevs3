"""
md_scraper.py

Description:
This script is designed to convert HTML files into Markdown format. It can handle both local HTML files and directories, as well as remote HTML files accessed via URLs. The script downloads any media files (images and videos) linked within the HTML and saves them locally, ensuring that the Markdown output references these local copies.

Usage:
- To convert a single local HTML file:
  python md_scraper.py /path/to/file.html --folder /path/to/output

- To convert all HTML files in a directory:
  python md_scraper.py /path/to/directory --folder /path/to/output

- To convert a remote HTML file:
  python md_scraper.py http://example.com/file.html --folder /path/to/output

Parameters:
- path: The path to a local HTML file, a directory containing HTML files, or a URL to a remote HTML file.
- --folder: The output directory where the converted Markdown files and media will be saved. Defaults to 'output' if not specified.

Features:
- Converts HTML content to Markdown using a custom converter.
- Downloads and saves media files (images and videos) locally.
- Handles both single files and directories.
- Processes remote HTML files accessed via URLs.
- Provides a summary of the conversion process, including success and failure counts.

Dependencies:
- requests: For handling HTTP requests.
- markdownify: For converting HTML to Markdown.
- yt_dlp: For downloading videos.
- magic: For determining file types.
- glob: For file pattern matching.

Logging:
The script logs its progress and any errors encountered during the conversion process. Logs are output to the console with timestamps and severity levels.

Author:
    [PvP]

Date:
    [15.12.2024]

"""

import argparse
import logging
import os
import re
import requests
import urllib.parse
import shutil
from pathlib import Path
from markdownify import MarkdownConverter
import yt_dlp
import magic
import glob

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

class CustomMarkdownConverter(MarkdownConverter):
    def __init__(self, **options):
        self.media_folder = options.pop('media_folder', None)
        self.base_url = options.pop('base_url', '')
        self.summary = options.pop('summary', None)
        if 'strip' not in options:
            options['strip'] = []
        options['strip'].extend([
            'script',
            'style',
            'meta',
            'link',
            'noscript',
            'iframe[src*="easycart.pl"]',
        ])
        super().__init__(**options)

    def convert_style(self, el, text, convert_as_inline):
        """Remove style elements completely"""
        return ''

    def convert_script(self, el, text, convert_as_inline):
        """Remove script elements completely"""
        return ''

    def convert_meta(self, el, text, convert_as_inline):
        """Remove meta elements completely"""
        return ''

    def convert_figure(self, el, text, convert_as_inline):
        """Convert figure elements to markdown with local media files."""
        img_tag = el.find('img')
        if img_tag:
            src = img_tag.get('src')
            alt_text = img_tag.get('alt', '')
            
            filename = download_media_file(src, self.base_url, self.media_folder)
            if filename:
                if self.summary:
                    self.summary.downloads['images']['success'] += 1
                markdown_image = f'![{alt_text}](media/{filename})\n'
                
                figcaption = el.find('figcaption')
                if figcaption:
                    caption = figcaption.text.strip()
                    return f'{markdown_image}*{caption}*\n\n'
                return f'{markdown_image}\n'
            elif self.summary:
                self.summary.downloads['images']['failed'] += 1
        return ''

    def convert_iframe(self, el, text, convert_as_inline):
        """Convert iframe elements, specifically handling Vimeo videos."""
        src = el.get('src', '')
        
        # Skip easycart iframes
        if 'easycart.pl' in src:
            return ''
        
        # Handle Vimeo embeds
        if 'vimeo.com' in src:
            video_url = urllib.parse.unquote(src)
            video_id = extract_vimeo_id(video_url)
            if video_id:
                if check_media_exists(self.media_folder, f"{video_id}.mp4"):
                    if self.summary:
                        self.summary.downloads['videos']['success'] += 1
                    return f'![[media/{video_id}.mp4]]\n\n'
                    
                success = download_vimeo_video(video_url, self.media_folder, video_id)
                if success:
                    if self.summary:
                        self.summary.downloads['videos']['success'] += 1
                    return f'![[media/{video_id}.mp4]]\n\n'
                elif self.summary:
                    self.summary.downloads['videos']['failed'] += 1
        
        return ''

    def convert_img(self, el, text, convert_as_inline):
        """Convert img elements to markdown with local media files."""
        src = el.get('src')
        alt_text = el.get('alt', '')
        
        filename = download_media_file(src, self.base_url, self.media_folder)
        if filename:
            if self.summary:
                self.summary.downloads['images']['success'] += 1
            return f'![{alt_text}](media/{filename})\n'
        elif self.summary:
            self.summary.downloads['images']['failed'] += 1
        return ''

def parse_arguments():
    parser = argparse.ArgumentParser(description='Convert HTML to Markdown')
    parser.add_argument('path', help='URL or local path to HTML file or directory')
    parser.add_argument('--folder', default='output', help='Output folder for markdown files')
    return parser.parse_args()

def create_folders(base_folder):
    """Create base and media folders if they don't exist"""
    base_folder = Path(base_folder)
    media_folder = base_folder / 'media'
    base_folder.mkdir(parents=True, exist_ok=True)
    media_folder.mkdir(exist_ok=True)
    return base_folder, media_folder

def find_html_files(path):
    """Find HTML file(s) from given path"""
    path = Path(path)
    if path.is_file() and path.suffix.lower() == '.html':
        html_files = [path]
        logging.info(f"Processing single file: {path}")
    else:
        html_files = list(Path(path).glob('**/*.html'))
        logging.info(f"Found {len(html_files)} HTML files in folder")
    return html_files

def download_media_file(url, base_url, media_folder):
    """Download media file and return filename using flat structure with extension"""
    if not url.startswith(('http://', 'https://')):
        url = urllib.parse.urljoin(base_url, url)
    
    try:
        parsed_url = urllib.parse.urlparse(url)
        # Create a flat filename from the URL path
        flat_filename = f"{parsed_url.netloc}{parsed_url.path}".replace('/', '_')
        
        # Use glob to check for any existing file with the base filename
        existing_files = glob.glob(f"{media_folder}/{flat_filename}.*")
        if existing_files:
            logging.info(f"File already exists: {existing_files[0]}")
            return Path(existing_files[0]).name
        
        # If no existing file, proceed to download
        filepath = Path(media_folder) / flat_filename
        logging.info(f"Downloading: {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            shutil.copyfileobj(response.raw, f)
        logging.info(f"Saved to: {filepath}")
        
        # Determine the file type using magic
        mime = magic.Magic(mime=True)
        mime_type = mime.from_file(str(filepath))
        extension = mime_type.split('/')[-1]
        
        # Ensure the extension is valid
        valid_extensions = ['jpeg', 'jpg', 'png', 'gif', 'bmp', 'webp']
        if extension not in valid_extensions:
            logging.error(f"Unsupported file type: {mime_type}")
            return None
        
        # Manually append the correct extension
        new_filepath = filepath.parent / f"{filepath.name}.{extension}"
        if not new_filepath.exists():
            filepath.rename(new_filepath)
        return new_filepath.name
    except Exception as e:
        logging.error(f"Failed to download {url}: {str(e)}")
        return None

def check_media_exists(media_folder, filename):
    """Check if media file already exists"""
    media_path = Path(media_folder) / filename
    return media_path.exists()

def extract_vimeo_id(url):
    """Extract Vimeo video ID from URL"""
    patterns = [
        r'vimeo\.com/video/(\d+)',
        r'vimeo\.com/(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def download_vimeo_video(url, media_folder, video_id):
    """Download Vimeo video using yt-dlp if it doesn't exist"""
    video_path = Path(media_folder) / f"{video_id}.mp4"
    
    if video_path.exists():
        logging.info(f"Video already exists: {video_path}")
        return True
    
    options = {
        'outtmpl': str(video_path),
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
    }
    
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            logging.info(f"Downloading video: {url}")
            ydl.download([url])
            logging.info("Download complete!")
            return True
    except Exception as e:
        logging.error(f"Failed to download video: {str(e)}")
        return False

def convert_html_to_markdown(html_content, media_folder, base_url, summary):
    """Convert HTML to Markdown using custom converter"""
    # Remove AI_devs Ag3nts text if present
    html_content = re.sub(r'AI_devs\s+Ag3nts', '', html_content, flags=re.IGNORECASE)
    
    # Remove window._EC_HASH script content
    html_content = re.sub(
        r'!window\._EC_HASH_[a-f0-9]+\s*&&\s*\(location\.href\s*=\s*"[^"]+"\);',
        '',
        html_content
    )
    
    # Remove all CSS style blocks
    html_content = re.sub(
        r'<style[^>]*>.*?</style>',
        '',
        html_content,
        flags=re.DOTALL | re.IGNORECASE
    )
    
    # Remove inline styles
    html_content = re.sub(
        r'\s*style\s*=\s*"[^"]*"',
        '',
        html_content
    )
    
    # Remove specific CSS patterns
    patterns_to_remove = [
        r'@media\s*\([^{]+\)\s*{[^}]*}',
        r'body\s*{[^}]*}',
        r'body\s+[a-z]+\s*{[^}]*}',
        r'body\s+[a-z]+:[a-z]+\s*{[^}]*}',
        r'iframe,\s*img\s*{[^}]*}',
        r'iframe\s*{[^}]*}',
        r'br\s*{[^}]*}',
        r':root\s*{[^}]*}',
        r'[a-z]+\s*{[^}]*max-width:\s*[^}]*}',
        r'[a-z]+\s*{[^}]*margin[^}]*}',
        r'[a-z]+\s*{[^}]*padding[^}]*}',
        r'[a-z]+\s*{[^}]*font[^}]*}',
        r'[a-z]+\s*{[^}]*color[^}]*}',
        r'[a-z]+\s*{[^}]*background[^}]*}',
        r'[a-z]+\s*{[^}]*display[^}]*}',
        r'[a-z]+\s*{[^}]*text-decoration[^}]*}',
        r'[a-z]+\s*{[^}]*list-style[^}]*}'
    ]
    
    for pattern in patterns_to_remove:
        html_content = re.sub(pattern, '', html_content, flags=re.MULTILINE|re.DOTALL)
    
    converter = CustomMarkdownConverter(
        media_folder=media_folder,
        base_url=base_url,
        summary=summary,
        strip=['script', 'style', 'meta', 'link', 'noscript'],
        extras=['tables', 'fenced-code-blocks']
    )
    
    # Convert to markdown
    markdown = converter.convert(html_content)
    
    # Final cleanup of any remaining CSS-like content
    markdown = re.sub(r'\n\s*@media[^}]+}\s*\n', '\n', markdown)
    markdown = re.sub(r'\n\s*body[^}]+}\s*\n', '\n', markdown)
    markdown = re.sub(r'\n\s*:root[^}]+}\s*\n', '\n', markdown)
    markdown = re.sub(r'\n\s*[a-z]+\s*{[^}]*}\s*\n', '\n', markdown)
    
    # Remove multiple consecutive blank lines
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
    
    # Remove any remaining CSS variable references
    markdown = re.sub(r'var\(--[^)]+\)', '', markdown)
    
    return markdown.strip()

def process_html_files(html_files, base_folder, media_folder, summary):
    """Process each HTML file and convert to Markdown"""
    for html_file in html_files:
        logging.info(f"Processing: {html_file}")
        
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            base_url = f"file://{os.path.abspath(html_file)}"
            output_filename = os.path.splitext(html_file.name)[0] + '.md'
            
            # Convert to markdown
            markdown_content = convert_html_to_markdown(html_content, media_folder, base_url, summary)
            
            # Save markdown file with appropriate name
            output_file = base_folder / output_filename
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            summary.successful_files += 1
            logging.info(f"Conversion complete. Output saved to {output_file}")
        except Exception as e:
            summary.failed_files += 1
            summary.add_error(html_file, f"Failed to process file: {str(e)}")
            logging.error(f"Error processing {html_file}: {str(e)}")

def process_remote_html(url, base_folder, media_folder, summary):
    """Process a remote HTML file and convert to Markdown"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        html_content = response.text
        base_url = url
        
        # Extract filename from URL
        parsed_url = urllib.parse.urlparse(url)
        output_filename = Path(parsed_url.path).stem + '.md'
        
        # Convert to markdown
        markdown_content = convert_html_to_markdown(html_content, media_folder, base_url, summary)
        
        # Save markdown file with appropriate name
        output_file = base_folder / output_filename
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        summary.successful_files += 1
        logging.info(f"Conversion complete. Output saved to {output_file}")
    except Exception as e:
        summary.failed_files += 1
        summary.add_error(url, f"Failed to process URL: {str(e)}")
        logging.error(f"Error processing {url}: {str(e)}")

def main():
    args = parse_arguments()
    path = args.path
    
    summary = ProcessingSummary()
    
    try:
        base_folder, media_folder = create_folders(args.folder)
        
        if path.startswith(('http://', 'https://')):
            # Handle remote URL
            process_remote_html(path, base_folder, media_folder, summary)
        else:
            # Handle local file or directory
            path = Path(path)
            if not path.exists():
                logging.error(f"Path {path} does not exist")
                return
            
            html_files = find_html_files(path)
            summary.total_files = len(html_files)
            
            process_html_files(html_files, base_folder, media_folder, summary)
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
    finally:
        summary.print_summary()

if __name__ == '__main__':
    main() 