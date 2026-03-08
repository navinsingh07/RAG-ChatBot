## RAG Mutual Fund FAQ Chatbot – Architecture & Phase-wise Plan

### 1. Objectives & Scope

- **Goal**: Build a RAG-based FAQ chatbot that answers **only factual questions** about mutual fund schemes, primarily HDFC Mutual Fund schemes, using **Groww** pages for structured scheme data and **official sources (AMC / AMFI / SEBI)** for citations.
- **Supported facts (non-exhaustive)**:
  - Expense ratio
  - Exit load
  - Minimum SIP / minimum investment
  - ELSS lock-in period
  - Riskometer / risk level
  - Benchmark index
  - Fund size / AUM
  - Basic NAV info (current NAV, date)
  - How to download capital gains / account statements (process guidance only)
- **Hard constraints**:
  - **No investment advice**: no buy/sell/hold, no portfolio suggestions, no “best fund” answers.
  - **Factual-only answers**: answers must be grounded in retrieved context.
  - **Response format**:
    - Max **3 sentences**.
    - **Exactly one source link** per answer.
    - Must clearly state the requested fact.
    - Footer with “Last updated from sources: \<date\>”.
  - **Privacy**: do not store or request personal data (PAN, Aadhaar, phone, etc.).
  - **Scraping**:
    - Scrape only **HTML pages** from Groww for scheme data.
    - Do **not** download PDFs from Groww.
  - **Sources for citations**:
    - Only **official AMC website, AMFI, SEBI** pages.
    - Prefer HTML over large PDFs; if PDFs are unavoidable, keep to small scheme documents or specific sections.

---

### 2. High-level System Architecture

- **Client/UI** (React.js frontend)
  - Single-page UI built in **React.js** with a clean, modern design:
    - Welcome text: _“Ask factual questions about mutual fund schemes. Facts only. No investment advice.”_
    - Three clickable example queries:
      - “What is the expense ratio of HDFC Mid Cap Fund?”
      - “What is the lock-in period for ELSS?”
      - “How can I download a capital gains statement?”
    - Chat input + message history.
    - Display of answer, source link, and “Last updated from sources: \<date\>”.
- **Backend API**
  - HTTP API serving:
    - `/ask` – accepts user query, returns answer + source + metadata.
    - `/health` – health check.
  - Orchestration of RAG pipeline: query classification → retrieval → LLM → post-processing → guardrails.
- **Data & Retrieval Layer**
  - **Groww scheme datastore**:
    - Structured scheme-level data scraped from Groww:
      - Scheme name, category, expense ratio, exit load, min SIP, lock-in, risk level, benchmark, fund size, NAV info, etc.
      - Stored in JSON and/or a small relational/embedded DB (e.g. SQLite) for deterministic lookups.
  - **Document corpus** (official sources):
    - 15–25 curated URLs from AMC, AMFI, SEBI.
      - Scheme documents (factsheets, SID/KIM summaries, FAQs).
      - Riskometer, benchmark explanations.
      - How-to guides for capital gains / account statements.
    - Text chunks with metadata stored in a vector store.
  - **Vector store**:
    - Local store (e.g. Chroma/FAISS) holding embeddings for:
      - Official textual content (for explanations and confirmation of scheme facts).
      - Optional: textual representations of Groww scheme records (for cross-checking).
- **LLM & Inference**
  - **Groq API** for inference (e.g. suitable LLaMA or Mixtral model).
  - LLM is instructed to:
    - Answer **only using provided context**.
    - Never provide investment advice.
    - Respect answer length and formatting constraints.
  - Backend enforces additional hard guardrails regardless of LLM behavior.

---

### 3. Data Ingestion Architecture

#### 3.1 Groww Scraper Pipeline

**Input**: AMC landing page – `https://groww.in/mutual-funds/amc/hdfc-mutual-funds`  
**Output**: Structured JSON/DB records, one per scheme.

- **Step 1 – Crawl AMC page**
  - Fetch AMC page HTML (with respectful rate-limiting and user-agent).
  - Parse DOM to identify:
    - Scheme listing elements (cards/rows).
    - Links to individual scheme detail pages (e.g. `/mutual-funds/hdfc-mid-cap-fund-direct-growth`).
  - Produce a queue of scheme URLs.

- **Step 2 – Crawl scheme pages**
  - For each scheme URL:
    - Fetch scheme page HTML.
    - Extract structured fields using robust CSS/XPath selectors plus fallbacks:
      - `scheme_name`
      - `amc_name`
      - `category` / `sub_category`
      - `expense_ratio` (value + as-of date if available)
      - `exit_load` (text, including conditions)
      - `minimum_sip` (value + frequency, e.g. monthly)
      - `minimum_lumpsum`
      - `lock_in_period` (e.g. “3 years” for ELSS, or “No lock-in”)
      - `risk_level` (e.g. “Very High” Riskometer label)
      - `benchmark` (full benchmark index name)
      - `fund_size_aum`
      - `nav` and `nav_date`
      - `scheme_code`/`ISIN` if exposed.
      - `groww_scheme_url`
    - Normalize and validate numeric fields (e.g. `0.75%` → `0.0075` + formatted string).
    - Mark missing/unknown fields explicitly (e.g. `null` or “Not disclosed on Groww”).

- **Step 3 – Store scheme records**
  - Store each scheme as:
    - A JSON document in a `data/schemes/` folder, and/or
    - A row in a local DB (e.g. `schemes` table in SQLite).
  - Data model (conceptual):

    ```text
    Scheme {
      id: string                // internal id
      scheme_name: string
      amc_name: string
      category: string
      sub_category: string | null
      expense_ratio: {
        value_pct: float | null
        as_of: date | null
      }
      exit_load: string | null
      minimum_sip: {
        amount: float | null
        frequency: string | null
      }
      minimum_lumpsum: float | null
      lock_in_period: string | null
      risk_level: string | null
      benchmark: string | null
      fund_size_aum_cr: float | null
      nav: {
        value: float | null
        date: date | null
      }
      groww_scheme_url: string
      official_sources: OfficialSourceRef[] // pointers to AMC/AMFI/SEBI URLs
      last_scraped_at: datetime
    }
    ```

- **Step 4 – Link to official sources**
  - For each scheme, maintain references to 1–3 **official URLs**:
    - AMC scheme page/factsheet.
    - AMFI scheme snapshot.
    - SEBI/AMFI category-level explanations (e.g. ELSS lock-in, Riskometer details).
  - These URLs are not necessarily scraped deeply; they are used primarily for:
    - RAG context (if text is extracted).
    - Answer citations.

#### 3.2 Official Document Collector

**Goal**: Build a small curated corpus (15–25 URLs) from:
- HDFC Mutual Fund official site.
- AMFI (`amfiindia.com`).
- SEBI (`sebi.gov.in` or `investor.sebi.gov.in`, etc.).

**Steps**:
- **URL curation (manual + semi-automatic)**:
  - Manually identify core URLs:
    - For selected schemes (e.g. “HDFC Mid Cap Fund – Direct Plan – Growth Option”, “HDFC NIFTY Midcap 150 Index Fund – Direct Growth”).
    - ELSS lock-in explanations (category-level).
    - Riskometer definition pages.
    - Benchmark and index descriptions (if hosted on AMC/AMFI/SEBI).
    - Guides for downloading account statements and capital gains statements.
  - Save curated URLs into a `sources.csv` / `sources.md` file with metadata:
    - `url`, `domain`, `document_type`, `related_scheme`, `topic_tags`.

- **Content extraction**:
  - For HTML pages:
    - Fetch and extract visible text from main content regions (avoid nav, footers).
    - Retain headings, bullet lists, tables where possible.
  - For small PDFs (only if HTML not available and the doc is important, e.g. factsheet):
    - Extract text using a PDF parser.
    - Avoid large multi-MB PDFs; if needed, restrict to relevant pages.

- **Metadata tagging**:
  - Tag each chunk/doc with:
    - `scheme_name` (if scheme-specific) or `null` (for generic).
    - `source_url`.
    - `document_type` (e.g. `factsheet`, `faq`, `how_to`, `regulation`, `category_info`).
    - `publisher` (`HDFC`, `AMFI`, `SEBI`).
    - `as_of_date` or `last_updated_date` if available in the content.

---

### 4. Data Processing & Embeddings

#### 4.1 Text Cleaning & Normalization

- Normalize all ingested text:
  - Remove boilerplate nav/footer text.
  - Collapse excessive whitespace and line breaks.
  - Preserve tables and bullet lists where they carry factual content (e.g. charges table).
  - Standardize field names and units (e.g. percentages, currency, “years/months”).

#### 4.2 Chunking Strategy

- **Scheme-specific chunks**:
  - Combine key facts about a single scheme into compact chunks:
    - Example: a chunk containing expense ratio, exit load, minimum SIP, benchmark, and riskometer for one scheme.
  - Target chunk size: e.g. 300–700 tokens.
  - Ensure each chunk has:
    - Clear scheme identification (name, AMC).
    - One or more clearly stated facts.

- **Generic knowledge chunks**:
  - Pages like “What is ELSS and its lock-in period?” or “Riskometer explanation”:
    - Chunk by section/heading.
    - Each chunk covers one concept (e.g. ELSS rules, Riskometer categories, statement download process).

- **Metadata for chunks**:
  - `chunk_id`
  - `scheme_name` (if applicable)
  - `topic` (e.g. `expense_ratio`, `exit_load`, `lock_in`, `riskometer`, `benchmark`, `statements`)
  - `source_url`
  - `document_type`
  - `publisher`
  - `ingested_at`

#### 4.3 Embeddings & Vector Store

- **Embedding model**:
  - Use a sentence embedding model suitable for finance text (exact choice TBD; can start with a general-purpose model).
- **Vector store design**:
  - Store:
    - `embedding` vector.
    - Full `chunk_text`.
    - Metadata (as above).
  - Index fields for efficient filtering:
    - By `scheme_name`.
    - By `topic`.
    - By `publisher`.

---

### 5. Retrieval & Answering Flow

#### 5.1 Query Understanding

- **Classifier / router** (lightweight heuristic or small model):
  - Detect:
    - **Factual scheme query** (e.g. “expense ratio of HDFC Mid Cap Fund”).
    - **Generic MF rules** (e.g. “What is the lock-in period for ELSS?”).
    - **Process query** (e.g. “How can I download a capital gains statement?”).
    - **Investment advice** (e.g. “Should I invest in this fund?”, “Which fund is best?”).
  - If classified as **investment advice / recommendation / portfolio query**:
    - Skip retrieval, return **refusal response** (see Guardrails).

- **Scheme detection**:
  - Use fuzzy matching over known `scheme_name` entries from the Groww scheme datastore:
    - Normalize user input (case, punctuation, “direct plan”, “growth” vs “regular”, etc.).
    - Map to canonical internal `scheme_id` if similarity passes threshold.

#### 5.2 Retrieval Strategy

- **For scheme-specific factual queries**:
  1. Identify candidate scheme(s) from scheme datastore.
  2. Retrieve:
     - Deterministic fields directly from structured scheme record (Groww-based).
     - 3–6 top chunks from vector store filtered by `scheme_name` and relevant `topic` (e.g. `expense_ratio`, `benchmark`).
  3. Prepare RAG context:
     - Structured fact block from scheme record (marked as “scraped from Groww”).
     - Text chunks from **official sources** (AMC/AMFI/SEBI) that confirm or define the fact.
  4. Select a **single official URL** from the retrieved chunks as the citation to show in the final answer.

- **For generic concept queries (ELSS, Riskometer, statements, etc.)**:
  1. Use embeddings-based retrieval over generic chunks (filter by topic).
  2. Use top-k chunks (e.g. k=5) as LLM context.
  3. Choose the most relevant official URL among those chunks as the single citation.

#### 5.3 LLM Prompting (Groq API)

- **System prompt** (conceptual):
  - You are a factual assistant for mutual fund schemes.
  - You must **only use the provided context**.
  - If the context does not contain the required fact, say you don’t know.
  - You must **never provide investment advice** or recommendations.
  - Responses must follow the required format (≤3 sentences, exactly one source link, factual tone, and footer).

- **RAG prompt structure**:
  - System: safety + style rules.
  - Context: concatenated scheme facts (structured → text) + retrieved chunks.
  - User: the user’s original question.

- **Post-processing**:
  - Enforce:
    - Max 3 sentences (truncate or ask model to regenerate if needed).
    - Exactly one URL (ensure chosen official source URL is injected as `Source: <url>` line; the model need not “decide” the URL).
    - Required footer with last-updated date (based on latest `ingested_at` / `last_scraped_at` of used chunks/facts).
  - Optionally perform a secondary “policy check” pass over the LLM’s draft answer (heuristics/regex to detect advice phrases, e.g. “you should invest”, “best fund”, “recommended for you”), and if triggered, replace with a refusal template.

#### 5.4 Guardrails & Refusal Flow

- **Trigger conditions**:
  - Query intent classified as:
    - “investment advice”, “recommendation”, “portfolio construction”, “tax advice”.
  - Answer content (draft) contains advice-style language.

- **Refusal response template** (example):
  - Body (1–2 sentences):
    - “I can’t provide investment advice or recommend specific funds, but I can share factual information about mutual fund schemes such as expense ratios, lock-in periods, and risk levels.”
  - Source line (1 sentence):
    - “Source: \<AMFI or SEBI educational resource URL\>”
  - Footer:
    - “Last updated from sources: \<date\>”

- Ensure the refusal still obeys:
  - ≤3 sentences total (body + source + footer).
  - Exactly one citation link (e.g. an AMFI investor education page).

---

### 6. UI & Interaction Design

- **Layout**:
  - Compact chat container implemented as a **React.js** single-page app with a visually polished, responsive design (good typography, spacing, and basic theming) with:
    - Static banner text (disclaimer):
      - “Ask factual questions about mutual fund schemes. Facts only. No investment advice.”
    - 3 example query buttons or clickable text:
      - “What is the expense ratio of HDFC Mid Cap Fund?”
      - “What is the lock-in period for ELSS?”
      - “How can I download a capital gains statement?”
    - Text input area and send button.
    - Message list showing alternating user and assistant messages.

- **Message rendering**:
  - Assistant message sections:
    - Main answer (1–2 sentences).
    - `Source: <clickable link>` (single link).
    - `Last updated from sources: <date>` (small, muted text).
  - Explicit reminder not to treat responses as investment advice (may appear as a fixed footer or tooltip).

---

### 7. Deliverables Mapping

- **1. Working prototype (app or notebook)**:
  - Backend service exposing `/ask` endpoint, wired to Groq API and vector store.
  - Simple web UI or notebook widgets to interact with the chatbot.

- **2. Source list (CSV or Markdown) with 15–25 URLs**:
  - `sources.csv` / `sources.md` maintained by the official document collector.
  - Columns: `url`, `publisher`, `document_type`, `related_scheme`, `topic_tags`, `last_checked`.

- **3. README**:
  - Document:
    - Chosen AMC: HDFC Mutual Fund.
    - Selected schemes, e.g.:
      - HDFC Mid Cap Fund – Direct Plan – Growth Option.
      - HDFC NIFTY Midcap 150 Index Fund – Direct Growth.
    - Setup instructions:
      - Environment setup.
      - How to run the Groww scraper.
      - How to build embeddings and start the backend/UI.
    - Known limitations:
      - Data freshness (scrape schedule).
      - Coverage limited to HDFC schemes and selected official documents.
      - Possible structural changes on Groww/official sites breaking scrapers.

- **4. Sample Q&A file**:
  - `sample_qa.md` or `sample_qa.json`:
    - 5–10 example pairs with:
      - `question`
      - `answer_text`
      - `source_url`
      - `last_updated`
    - Include examples for:
      - Expense ratio, minimum SIP, benchmark, ELSS lock-in, capital gains statement download.

- **5. Disclaimer text used in the UI**:
  - Example disclaimer:
    - “This chatbot provides factual information about mutual fund schemes (e.g., expense ratios, exit loads, lock-in periods, and risk levels) based on publicly available sources. It does **not** provide investment advice, recommendations, or opinions. Please consult a SEBI-registered investment adviser for personalized advice.”

---

### 8. Phase-wise Implementation Plan

#### Phase 0 – Project Setup & Scoping

- Initialize repository structure (backend, data, notebooks, UI).
- Configure environment for:
  - HTTP requests & HTML parsing (for scraping).
  - PDF parsing (only for small official docs when needed).
  - Embedding model and vector store.
  - Groq API client.
- Draft and finalize the **disclaimer** and answer format templates.

#### Phase 1 – Data Collection (Groww + Official Sources)

- **Groww scraper**:
  - Implement crawler for HDFC AMC page and scheme pages.
  - Validate scraping selectors with at least:
    - HDFC Mid Cap Fund – Direct Plan – Growth Option.
    - HDFC NIFTY Midcap 150 Index Fund – Direct Growth.
  - Serialize scheme data into JSON/SQLite with the defined schema.
- **Official sources**:
  - Manually curate 15–25 URLs across AMC, AMFI, SEBI.
  - Implement HTML extractor (and minimal PDF handling if necessary).
  - Tag and persist raw text plus metadata.
- **Deliverables**:
  - Initial `sources.csv` / `sources.md`.
  - Raw data dumps under `data/`.

#### Phase 2 – Processing, Embeddings & Vector Store

- Implement cleaning and chunking for:
  - Scheme-specific factual text (from both Groww and official docs).
  - Generic concept pages (ELSS, Riskometer, statements).
- Generate embeddings for all chunks.
- Populate vector store with chunks and metadata.
- Build deterministic scheme lookup service on top of Groww datastore:
  - Fuzzy matching for scheme names.
  - Direct access to structured fields (e.g. `expense_ratio`, `minimum_sip`).

#### Phase 3 – RAG Backend with Guardrails

- Implement backend `/ask` endpoint:
  - Query classification (factual scheme vs generic vs advice).
  - Scheme detection and mapping.
  - Retrieval from vector store with appropriate filters.
  - Construction of RAG prompt for Groq API.
  - Post-processing to enforce:
    - ≤3 sentences.
    - Exactly one citation link from official sources.
    - Required footer with last-updated date.
  - Guardrail logic for:
    - Investment advice detection and refusal template.
    - “I don’t know” behavior when facts are missing from context.
- Add logging for:
  - Queries.
  - Retrieved chunks and chosen source URLs.
  - Final answer and any guardrail triggers.

#### Phase 4 – UI, Evaluation & Documentation

- **UI**:
  - Build a minimal, modern web UI or notebook interface:
    - Welcome message + disclaimer.
    - Example queries.
    - Chat interaction with formatted answer, source link, and footer.
- **Evaluation**:
  - Create `sample_qa` file with 5–10 representative questions.
  - Run queries through the system and verify:
    - Factual correctness vs official sources.
    - Exactly one citation link and ≤3 sentences.
    - Correct refusal behavior on advice queries.
- **Documentation**:
  - Complete `README` with setup, usage, and limitations.
  - Finalize `sources` list and Q&A examples.

---

### 9. Non-Functional Considerations

- **Freshness**:
  - Provide a simple re-scrape / re-ingest command to update data periodically.
  - Use `last_scraped_at` and `ingested_at` for the “Last updated from sources” footer.
- **Robustness**:
  - Handle missing or inconsistent data from Groww gracefully.
  - Fail closed on policy: if uncertain whether a query is advice, treat it as advice and refuse.
- **Extensibility**:
  - Design schema and pipelines so other AMCs or distributors can be added later with minimal changes.

