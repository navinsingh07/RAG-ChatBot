from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import json
from datetime import datetime
from typing import List, Optional
from groq import Groq
from dotenv import load_dotenv
import re

from processor.vector_store_manager import VectorStoreManager
from processor.scheme_service import SchemeService

# Load environment variables
load_dotenv()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="RAG Mutual Fund FAQ Chatbot")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with specific UI origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
vsm = VectorStoreManager()
scheme_service = SchemeService()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str
    source: str
    last_updated: str
    is_advice: bool

DISCLAIMER = """
This chatbot provides factual information about mutual fund schemes based on publicly available sources. 
It does NOT provide investment advice, recommendations, or opinions.
"""

def classify_intent(query: str) -> str:
    """Detect if the query is seeking investment advice."""
    advice_keywords = [
        "should i invest", "best fund", "recommend", "suggest", 
        "where to put money", "good for me", "buy", "sell", "hold",
        "portfolio", "returns", "prediction", "future"
    ]
    query_lower = query.lower()
    if any(k in query_lower for k in advice_keywords):
        return "ADVICE"
    return "FACTUAL"

def get_refusal_response() -> QueryResponse:
    return QueryResponse(
        answer="I can't provide investment advice or recommend specific funds, but I can share factual information about mutual fund schemes such as expense ratios, lock-in periods, and risk levels.",
        source="https://www.amfiindia.com/investor-corner/knowledge-center/index.html",
        last_updated=datetime.now().strftime("%Y-%m-%d"),
        is_advice=True
    )

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/ask", response_model=QueryResponse)
async def ask_question(request: QueryRequest):
    query = request.query.strip()
    
    # 1. Intent Classification (Guardrail)
    intent = classify_intent(query)
    if intent == "ADVICE":
        return get_refusal_response()

    # 2. Retrieval
    # Try to find a scheme mentioned in the query
    detected_scheme = scheme_service.get_scheme_by_name(query)
    
    # Search vector store for context
    # Use the scheme name as a filter if detected to improve accuracy
    where_filter = None
    if detected_scheme:
        where_filter = {"scheme_name": detected_scheme["scheme_name"]}
    
    search_results = vsm.search(query, n_results=5)
    context_chunks = search_results['documents'][0]
    metadatas = search_results['metadatas'][0]
    
    if not context_chunks:
        raise HTTPException(status_code=404, detail="No relevant information found.")

    # Select the most relevant official source for citation
    # Prefer HDFC, AMFI, or SEBI over Groww (Groww is for structured data)
    best_source = "https://www.amfiindia.com"
    for meta in metadatas:
        if "groww" not in meta.get("source_url", "").lower():
            best_source = meta.get("source_url")
            break

    # 3. LLM Generation
    context_text = "\n---\n".join(context_chunks)
    
    system_prompt = f"""
You are a factual assistant for HDFC Mutual Fund schemes.
RULES:
1. ONLY use the provided context to answer. 
2. If context lacks the fact, say "I do not have factual information for that."
3. NO investment advice, NO "best" or "should invest" phrases.
4. Response MUST be MAX 3 sentences.
5. Tone: Factual, professional, non-advisory.

DISCLAIMER: {DISCLAIMER}
"""

    user_prompt = f"CONTEXT:\n{context_text}\n\nQUESTION: {query}"

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=150
        )
        
        answer = completion.choices[0].message.content.strip()
        
        # Post-processing Guardrail: Ensure no advice language in LLM output
        if classify_intent(answer) == "ADVICE":
             return get_refusal_response()

        return QueryResponse(
            answer=answer,
            source=best_source,
            last_updated=datetime.now().strftime("%Y-%m-%d"),
            is_advice=False
        )

    except Exception as e:
        print(f"Groq API Error: {e}")
        raise HTTPException(status_code=500, detail="Error generating response.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
