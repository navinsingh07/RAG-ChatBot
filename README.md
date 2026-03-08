# RAG Mutual Fund FAQ Chatbot (HDFC Mutual Fund)

A Retrieval-Augmented Generation (RAG) chatbot designed to provide 100% factual information about HDFC Mutual Fund schemes. It uses **Playwright** for web scraping Groww for structured facts and **ChromaDB** for vector search across official AMC, AMFI, and SEBI documents.

## 🚀 Features
- **Factual-Only Answers**: Specifically trained to answer questions about expense ratios, exit loads, NAV, SIP, and more.
- **Investment Advice Guardrails**: Automatically detects and refuses requests for investment advice or "best fund" recommendations.
- **Official Citations**: Every answer includes a link to an official source (AMC/AMFI/SEBI).
- **Modern UI**: A clean, responsive chat interface inspired by modern fintech applications.
- **High Performance**: Powered by **Groq (Llama 3.3)** for near-instant inference.

## 🛠️ Tech Stack
- **Frontend**: React.js (Vite), Vanilla CSS
- **Backend**: FastAPI (Python), Uvicorn
- **AI/LLM**: Groq Cloud API (Llama 3.3 70B)
- **Vector Database**: ChromaDB
- **Embeddings**: Sentence-Transformers (`all-MiniLM-L6-v2`)
- **Scraping**: Playwright (Headless Chromium)

## 📋 Prerequisites
- Python 3.10+
- Node.js & npm
- [Groq API Key](https://console.groq.com/)

## 🔧 Setup Instructions

### 1. Clone & Environment
```bash
git clone <your-repo-url>
cd RAG-ChatBot
```

### 2. Backend Setup
```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your GROQ_API_KEY
```

### 3. Data Collection (Scraping)
```bash
# Run the Playwright scraper
python scraper/groww_scraper.py
```

### 4. Processing & Embeddings
```bash
# Fetch official documents and build the vector store
python processor/document_collector.py
python processor/vector_store_manager.py
```

### 5. Running the Application
**Start Backend:**
```bash
python -m backend.main
```
**Start Frontend:**
```bash
cd ui
npm install
npm run dev
```

## 🛡️ Guardrails & Safety
- **Length Constraint**: Responses are limited to a maximum of 3 sentences.
- **Source Verification**: Only official government or AMC links are provided as citations.
- **Intent Detection**: Keywords like "best", "invest", "recommend" trigger a polite refusal.

## 📄 Disclaimer
This chatbot provides factual information only. It does not provide investment advice. Please consult a SEBI-registered investment adviser for personalized recommendations.

---
Powered by **HDFC RAG-Agent**
