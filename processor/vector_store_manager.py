import chromadb
from sentence_transformers import SentenceTransformer
import os
import json
import pandas as pd
import uuid

class VectorStoreManager:
    def __init__(self, db_path="data/vector_store", model_name="all-MiniLM-L6-v2"):
        self.client = chromadb.PersistentClient(path=db_path)
        self.model = SentenceTransformer(model_name)
        self.collection = self.client.get_or_create_collection(
            name="mutual_fund_facts",
            metadata={"hnsw:space": "cosine"}
        )

    def process_and_store(self, processed_sources_csv="data/sources_processed.csv", schemes_dir="data/schemes"):
        # 1. Process Official Documents
        if os.path.exists(processed_sources_csv):
            df = pd.read_csv(processed_sources_csv)
            for _, row in df.iterrows():
                if pd.isna(row['raw_text_path']): continue
                
                with open(row['raw_text_path'], 'r', encoding='utf-8') as f:
                    text = f.read()
                
                chunks = self._chunk_text(text)
                for i, chunk in enumerate(chunks):
                    metadata = {
                        "source_url": str(row['url']),
                        "publisher": str(row['publisher']),
                        "doc_type": str(row['document_type']),
                        "topic_tags": str(row['topic_tags']),
                        "chunk_index": i
                    }
                    self.add_chunk(chunk, metadata)

        # 2. Process Scheme JSONs (Structured Facts)
        for filename in os.listdir(schemes_dir):
            if filename.endswith(".json"):
                with open(os.path.join(schemes_dir, filename), 'r', encoding='utf-8') as f:
                    scheme_data = json.load(f)
                
                # Create a factual summary chunk for the scheme
                summary = f"Scheme: {scheme_data['scheme_name']}\n"
                summary += f"AMC: {scheme_data['amc_name']}\n"
                summary += f"Expense Ratio: {scheme_data['expense_ratio']}\n"
                summary += f"Min SIP: {scheme_data['minimum_sip']}\n"
                summary += f"Risk Level: {scheme_data['risk_level']}\n"
                summary += f"Exit Load: {scheme_data['exit_load']}\n"
                summary += f"Benchmark: {scheme_data['benchmark']}\n"
                summary += f"NAV: {scheme_data.get('nav', 'N/A')} as of {scheme_data.get('nav_date', 'N/A')}\n"
                
                metadata = {
                    "scheme_name": str(scheme_data['scheme_name']),
                    "source_url": str(scheme_data['groww_scheme_url']),
                    "publisher": "Groww (Data Provider)",
                    "doc_type": "structured_fact",
                    "id": str(scheme_data.get('scheme_id', filename))
                }
                self.add_chunk(summary, metadata)

    def _chunk_text(self, text, max_chars=1000, overlap=200):
        # Basic character-based chunking with overlap
        chunks = []
        if len(text) <= max_chars:
            return [text]
            
        start = 0
        while start < len(text):
            end = start + max_chars
            chunks.append(text[start:end])
            start += max_chars - overlap
        return chunks

    def add_chunk(self, text, metadata):
        embedding = self.model.encode(text).tolist()
        self.collection.add(
            ids=[str(uuid.uuid4())],
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[text]
        )

    def search(self, query, n_results=5, where=None):
        query_embedding = self.model.encode(query).tolist()
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where
        )

if __name__ == "__main__":
    manager = VectorStoreManager()
    manager.process_and_store()
    print("Vector store populated.")
