import pandas as pd
import requests
from bs4 import BeautifulSoup
import io
import os
import json
from PyPDF2 import PdfReader
from datetime import datetime

class DocumentCollector:
    def __init__(self, sources_csv="data/sources.csv", raw_data_dir="data/raw"):
        self.sources_csv = sources_csv
        self.raw_data_dir = raw_data_dir
        if not os.path.exists(self.raw_data_dir):
            os.makedirs(self.raw_data_dir)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def fetch_all_sources(self):
        if not os.path.exists(self.sources_csv):
            print(f"Sources file {self.sources_csv} not found.")
            return
        
        df = pd.read_csv(self.sources_csv)
        processed_data = []

        for _, row in df.iterrows():
            url = row['url']
            print(f"Fetching: {url}")
            content = None
            
            try:
                if url.endswith('.pdf'):
                    content = self._fetch_pdf(url)
                else:
                    content = self._fetch_html(url)
                
                if content:
                    # Save raw text
                    filename = url.split('/')[-1].replace('.html', '').replace('.pdf', '')
                    if not filename: filename = "index"
                    filename = "".join([c if c.isalnum() else "_" for c in filename])[:50]
                    save_path = os.path.join(self.raw_data_dir, f"{filename}.txt")
                    
                    with open(save_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    new_row = row.copy()
                    new_row['raw_text_path'] = save_path
                    new_row['fetched_at'] = datetime.now().strftime("%Y-%m-%d")
                    processed_data.append(new_row)
            except Exception as e:
                print(f"Error fetching {url}: {e}")

        # Update sources with text paths
        if processed_data:
            processed_df = pd.DataFrame(processed_data)
            processed_df.to_csv("data/sources_processed.csv", index=False)
            print(f"Updated sources saved to data/sources_processed.csv ({len(processed_df)} records)")
        else:
            print("No data was fetched successfully.")

    def _fetch_html(self, url):
        response = requests.get(url, headers=self.headers, timeout=15)
        response.raise_for_status()
        # Explicitly set encoding to utf-8
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove nav, footers, scripts
        for tag in soup(['nav', 'footer', 'script', 'style', 'header']):
            tag.decompose()
            
        return soup.get_text(separator=' ', strip=True)

    def _fetch_pdf(self, url):
        response = requests.get(url, headers=self.headers, timeout=15)
        response.raise_for_status()
        
        with io.BytesIO(response.content) as f:
            reader = PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text

if __name__ == "__main__":
    collector = DocumentCollector()
    collector.fetch_all_sources()
