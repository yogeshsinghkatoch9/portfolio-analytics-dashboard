#!/usr/bin/env python3
"""
Confluence Documentation Sync Tool
Automatically uploads deployment guides, API docs, PRDs, and walkthroughs to Confluence
"""

import os
import requests
import base64
from pathlib import Path
from dotenv import load_dotenv
import markdown
from datetime import datetime

# Load environment variables
load_dotenv()

class ConfluenceSync:
    def __init__(self):
        self.url = os.getenv('CONFLUENCE_URL')
        self.email = os.getenv('CONFLUENCE_EMAIL')
        self.api_token = os.getenv('CONFLUENCE_API_TOKEN')
        self.space_key = os.getenv('CONFLUENCE_SPACE_KEY')
        self.parent_page_id = os.getenv('CONFLUENCE_PARENT_PAGE_ID', '')
        
        # Create auth header
        auth_string = f"{self.email}:{self.api_token}"
        auth_bytes = auth_string.encode('ascii')
        base64_bytes = base64.b64encode(auth_bytes)
        base64_auth = base64_bytes.decode('ascii')
        
        self.headers = {
            'Authorization': f'Basic {base64_auth}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
    def markdown_to_confluence(self, md_content):
        """Convert Markdown to Confluence Storage Format"""
        # Convert markdown to HTML first
        html = markdown.markdown(md_content, extensions=['extra', 'codehilite'])
        
        # Basic conversion to Confluence storage format
        # Replace code blocks
        html = html.replace('<pre><code>', '<ac:structured-macro ac:name="code"><ac:plain-text-body><![CDATA[')
        html = html.replace('</code></pre>', ']]></ac:plain-text-body></ac:structured-macro>')
        
        return html
    
    def find_page(self, title):
        """Find existing page by title"""
        url = f"{self.url}/wiki/rest/api/content"
        params = {
            'title': title,
            'spaceKey': self.space_key,
            'expand': 'version'
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            results = response.json().get('results', [])
            return results[0] if results else None
        return None
    
    def create_page(self, title, content, parent_id=None):
        """Create new Confluence page"""
        url = f"{self.url}/wiki/rest/api/content"
        
        # Convert markdown to Confluence format
        confluence_content = self.markdown_to_confluence(content)
        
        data = {
            'type': 'page',
            'title': title,
            'space': {'key': self.space_key},
            'body': {
                'storage': {
                    'value': confluence_content,
                    'representation': 'storage'
                }
            }
        }
        
        # Add parent if specified
        if parent_id or self.parent_page_id:
            data['ancestors'] = [{'id': parent_id or self.parent_page_id}]
        
        response = requests.post(url, headers=self.headers, json=data)
        
        if response.status_code == 200:
            print(f"✅ Created page: {title}")
            return response.json()
        else:
            print(f"❌ Failed to create page: {title}")
            print(f"   Error: {response.text}")
            return None
    
    def update_page(self, page_id, title, content, version):
        """Update existing Confluence page"""
        url = f"{self.url}/wiki/rest/api/content/{page_id}"
        
        # Convert markdown to Confluence format
        confluence_content = self.markdown_to_confluence(content)
        
        data = {
            'version': {'number': version + 1},
            'title': title,
            'type': 'page',
            'body': {
                'storage': {
                    'value': confluence_content,
                    'representation': 'storage'
                }
            }
        }
        
        response = requests.put(url, headers=self.headers, json=data)
        
        if response.status_code == 200:
            print(f"✅ Updated page: {title}")
            return response.json()
        else:
            print(f"❌ Failed to update page: {title}")
            print(f"   Error: {response.text}")
            return None
    
    def sync_page(self, title, content, parent_id=None):
        """Sync page to Confluence (create or update)"""
        existing_page = self.find_page(title)
        
        if existing_page:
            # Update existing page
            page_id = existing_page['id']
            version = existing_page['version']['number']
            return self.update_page(page_id, title, content, version)
        else:
            # Create new page
            return self.create_page(title, content, parent_id)
    
    def sync_file(self, file_path, title=None):
        """Sync a markdown file to Confluence"""
        path = Path(file_path)
        
        if not path.exists():
            print(f"❌ File not found: {file_path}")
            return None
        
        # Use filename as title if not provided
        if not title:
            title = path.stem.replace('_', ' ').title()
        
        # Read file content
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add metadata header
        header = f"""
<ac:structured-macro ac:name="info">
    <ac:rich-text-body>
        <p><strong>Last Updated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Source:</strong> {path.name}</p>
    </ac:rich-text-body>
</ac:structured-macro>

"""
        content_with_header = header + content
        
        return self.sync_page(title, content_with_header)


def main():
    """Main sync function"""
    print("🚀 Starting Confluence Sync...\n")
    
    # Initialize syncer
    syncer = ConfluenceSync()
    
    # Define documents to sync
    docs_to_sync = [
        {
            'file': 'README.md',
            'title': 'Portfolio Analytics Dashboard - Overview'
        },
        {
            'file': '.gemini/antigravity/brain/5561f775-5d72-45d8-8db1-e021fb4652a8/walkthrough.md',
            'title': 'Deployment Walkthrough'
        },
        {
            'file': 'backend/main.py',
            'title': 'API Documentation',
            'content': generate_api_docs()  # Custom function to generate API docs from code
        }
    ]
    
    # Sync each document
    for doc in docs_to_sync:
        if 'content' in doc:
            # Use provided content
            syncer.sync_page(doc['title'], doc['content'])
        else:
            # Sync from file
            syncer.sync_file(doc['file'], doc.get('title'))
    
    print("\n✅ Confluence sync complete!")


def generate_api_docs():
    """Generate API documentation from FastAPI app"""
    # This would parse your FastAPI routes and generate documentation
    # For now, returning a placeholder
    return """
# API Documentation

## Endpoints

### Health Check
`GET /health`

Returns the health status of the API.

### Portfolio Upload
`POST /upload-portfolio`

Upload a portfolio CSV/Excel file for analysis.

*More endpoints documented in Swagger UI at `/docs`*
"""


if __name__ == '__main__':
    main()
