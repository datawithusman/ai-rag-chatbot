# AI RAG Chatbot

A retrieval-augmented generation chatbot that lets you upload PDF documents and ask questions about their content. The system chunks the text, stores vector embeddings in ChromaDB, retrieves relevant passages for each question, and sends them as context to an LLM to generate grounded answers.

## How It Works

1. You upload a PDF through the web interface
2. The backend extracts text, splits it into overlapping chunks, and generates embeddings
3. Embeddings are stored in ChromaDB (persistent local vector store)
4. When you ask a question, the system searches for the most relevant chunks using cosine similarity
5. The top results are assembled into a prompt and sent to the LLM along with your question
6. The response includes source citations so you can verify the answer

## Architecture

```
Frontend (Next.js + Tailwind)
        |
        v
FastAPI Backend
   |          |
   v          v
LLM Service  Vector Store Service
(OpenAI)     (ChromaDB)
                   |
                   v
              Document Service
              (PDF parsing + chunking)
```

## Features

- PDF upload with automatic text extraction and smart chunking
- Cosine similarity search with configurable result count
- Source citations with page numbers and relevance scores
- Conversation history support for follow-up questions
- Demo mode when no API key is configured (returns retrieved context without LLM)
- Batch document management (upload, list, delete)
- Request logging and response timing middleware
- Docker Compose setup for one-command deployment

## Installation

### Backend

```bash
cd ai-rag-chatbot/backend
pip install -r requirements.txt
cp .env.example .env
# Add your OPENAI_API_KEY to .env
```

### Frontend

```bash
cd ai-rag-chatbot/frontend
npm install
```

### Docker (recommended)

```bash
cd ai-rag-chatbot
docker-compose up --build
```

This starts the backend on port 8000 and the frontend on port 3000.

## Configuration

Create a `.env` file in `backend/` based on `.env.example`:

```
OPENAI_API_KEY=sk-your-key-here
MODEL_NAME=gpt-4o-mini
TEMPERATURE=0.3
MAX_TOKENS=2000
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
CHROMA_PERSIST_DIR=./chroma_db
CHROMA_COLLECTION_NAME=documents
```

The app works without an API key in demo mode. It will still chunk and retrieve documents but will not call the LLM. Instead it returns the raw context so you can verify the retrieval pipeline.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Service health and uptime |
| POST | `/api/v1/documents/upload` | Upload a PDF for indexing |
| GET | `/api/v1/documents` | List all indexed documents |
| DELETE | `/api/v1/documents/{id}` | Remove a document and its chunks |
| POST | `/api/v1/chat` | Ask a question and get a grounded answer |
| GET | `/docs` | Swagger UI for interactive testing |

Example chat request:

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the refund policy?", "document_ids": ["doc_001"]}'
```

Example response:

```json
{
  "answer": "According to the document, refunds are available within 30 days of purchase...",
  "sources": [
    {
      "content": "Customers may request a full refund within 30 days...",
      "page_number": 4,
      "document_name": "company-policy.pdf",
      "relevance_score": 0.89
    }
  ],
  "conversation_id": "",
  "tokens_used": 342
}
```

## Tech Stack

- **Backend:** FastAPI, LangChain, ChromaDB, OpenAI
- **Frontend:** Next.js 14, React, Tailwind CSS
- **Infrastructure:** Docker, Docker Compose
- **CI:** GitHub Actions

## Project Structure

```
ai-rag-chatbot/
  backend/
    app/
      api/v1/        # Route handlers (chat, documents)
      core/          # Config, exceptions
      models/        # Pydantic schemas
      services/      # LLM, vector store, document processing
      tests/         # API tests
    Dockerfile
    requirements.txt
  frontend/
    src/app/         # Next.js App Router pages
    Dockerfile
    package.json
  docker-compose.yml
  .github/workflows/ # CI pipeline
```

## Running Tests

```bash
cd backend
pytest tests/ -v
```

## License

MIT