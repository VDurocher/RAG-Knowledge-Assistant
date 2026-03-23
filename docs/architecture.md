# Architecture — RAG Knowledge Assistant

## Overview

This system implements a Retrieval-Augmented Generation (RAG) pipeline designed
for production use in SMEs. It grounds every AI answer in company-specific documents,
eliminating hallucinations and providing traceable citations.

## Pipeline Diagram

```
User Question
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│                    STREAMLIT UI (app/main.py)                │
│  ┌───────────────────┐    ┌──────────────────────────────┐  │
│  │ Sidebar           │    │ Chat Interface               │  │
│  │ • Document list   │    │ • User input                 │  │
│  │ • Settings        │    │ • Streaming response         │  │
│  │ • Rebuild button  │    │ • Citations expander         │  │
│  └───────────────────┘    └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│                    RAG CHAIN (core/rag.py)                   │
│                                                             │
│  1. retriever.invoke(question)  →  top-k Document chunks    │
│  2. format_context(documents)   →  structured prompt ctx    │
│  3. prompt | llm | StrOutputParser()  →  streamed answer    │
│  4. Return (stream, source_documents)                       │
└─────────────────────────────────────────────────────────────┘
     │                                  │
     ▼                                  ▼
┌───────────────┐              ┌─────────────────┐
│ FAISS INDEX   │              │ OPENAI LLM      │
│ (core/indexer)│              │ gpt-4o-mini     │
│               │              │ (generation)    │
│ • Similarity  │              └─────────────────┘
│   search      │
│ • Disk cache  │
└───────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│                  DOCUMENT LOADER (core/loader.py)            │
│                                                             │
│  knowledge_base/                                            │
│  ├── report.pdf       →  PyPDFLoader   →  Document[]        │
│  ├── policy.txt       →  TextLoader    →  Document[]        │
│  └── guide.md         →  TextLoader    →  Document[]        │
└─────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. Smart Index Caching
The FAISS index is saved to disk after first build. On subsequent starts,
the system compares a hash of current source files against the saved manifest.
If unchanged, the index is loaded instantly (no re-embedding cost).

### 2. Dual Embedder Support
- **Local mode** (`EMBEDDER_TYPE=local`): `sentence-transformers/all-MiniLM-L6-v2`
  runs fully offline on CPU. Zero API cost for embeddings. Best for privacy-sensitive
  environments or high document volumes.
- **OpenAI mode** (`EMBEDDER_TYPE=openai`): `text-embedding-3-small` provides higher
  semantic accuracy, especially for domain-specific vocabulary.

### 3. Citation Architecture
Each document chunk retains `metadata["source"]` (filename) and `metadata["page"]`
(PDF page number). The retriever returns these alongside the text, enabling precise
citations without post-processing.

### 4. Streaming UX
`ask_stream()` uses LangChain's `.stream()` interface, fed directly into Streamlit's
`st.write_stream()`. The retrieval step completes before streaming starts, so citations
are always available when the answer begins.

## Directory Structure

```
RAG-Knowledge-Assistant/
├── app/
│   └── main.py              # Streamlit UI — single-file app
├── core/
│   ├── config.py            # Settings dataclass + .env loading
│   ├── loader.py            # Document loading (PDF, TXT, MD)
│   ├── indexer.py           # FAISS index build/load + text splitting
│   └── rag.py               # RAG chain, LLM, citations
├── knowledge_base/          # Drop your files here
├── vector_store/            # Auto-generated FAISS index (gitignored)
├── docs/
│   └── architecture.md      # This file
└── tests/
    ├── test_loader.py
    └── test_indexer.py
```

## Scaling Considerations

| Scale | Recommendation |
|-------|---------------|
| < 500 pages | FAISS in-memory (current setup, instant) |
| 500–10k pages | FAISS with disk persistence (current setup) |
| > 10k pages | Migrate to Chroma, Pinecone, or pgvector |
| Multi-tenant | Add namespace/collection per team |
| Async traffic | Replace Streamlit with FastAPI + WebSockets |
