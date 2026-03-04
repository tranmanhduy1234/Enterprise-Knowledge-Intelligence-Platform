# EKIP - Enterprise Knowledge Intelligence Platform 2.0

> Nền tảng trí tuệ tri thức doanh nghiệp — hệ thống RAG (Retrieval-Augmented Generation) toàn diện với Hybrid Search, Reranking và giao diện Chat AI.

---

## 📋 Mục lục

- [Tổng quan](#tổng-quan)
- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Công nghệ sử dụng](#công-nghệ-sử-dụng)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Chi tiết các thành phần](#chi-tiết-các-thành-phần)
  - [Backend API](#1-backend-api-app)
  - [Data Pipeline](#2-data-pipeline-pipeline)
  - [Frontend UI](#3-frontend-ui-ui)
  - [Hạ tầng](#4-hạ-tầng-infrastructure)
- [Luồng xử lý dữ liệu](#luồng-xử-lý-dữ-liệu)
- [API Endpoints](#api-endpoints)
- [Cách khởi chạy](#cách-khởi-chạy)
- [Cấu hình](#cấu-hình)

---

## Tổng quan

**EKIP** là một hệ thống RAG hoàn chỉnh, cho phép:
1. **Nạp tài liệu** (PDF, DOCX, PPTX, XLSX, Markdown, HTML) → chuyển đổi thành vector và lưu trữ.
2. **Truy vấn thông minh** bằng ngôn ngữ tự nhiên → tìm kiếm hybrid (Dense + Sparse) → Rerank → Sinh câu trả lời bằng LLM.
3. **Giao diện Chat** — trải nghiệm hỏi đáp giống ChatGPT trên nền tài liệu nội bộ.

---

## Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React/Vite)                    │
│              Chat UI — shadcn/ui + TailwindCSS                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP / REST API
┌──────────────────────────▼──────────────────────────────────────┐
│                     FastAPI Backend (:8000)                     │
│  ┌──────────┐  ┌────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │ /ingest  │  │  /query    │  │ /ingest/     │  │ /health   │  │
│  │          │  │            │  │  status/{id} │  │           │  │
│  └────┬─────┘  └─────┬──────┘  └──────────────┘  └───────────┘  │
│       │              │                                          │
│  ┌────▼─────┐  ┌─────▼──────────────────────────────┐           │
│  │ Celery   │  │         RAG Pipeline                │          │
│  │ Worker   │  │  Hybrid Retriever → Reranker → LLM │           │
│  └────┬─────┘  └─────┬──────────────────────────────┘           │
└───────┼──────────────┼──────────────────────────────────────────┘
        │              │
┌───────▼──────────────▼──────────────────────────────────────────┐
│                    Data & Storage Layer                         │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐     │
│  │   Qdrant    │  │    Redis     │  │  Semantic Cache     │     │
│  │ Vector DB   │  │  (Broker +   │  │  (Qdrant-based)     │     │
│  │ (:6333)     │  │   Cache)     │  │                     │     │
│  │             │  │  (:6379)     │  │                     │     │
│  └─────────────┘  └──────────────┘  └─────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Công nghệ sử dụng

| Tầng | Công nghệ | Vai trò |
|------|-----------|---------|
| **LLM** | Gemini 2.5 Flash Lite (API) | Sinh câu trả lời chính (production) |
| **LLM (local)** | Meta Llama-3-8B-Instruct | Sinh câu trả lời (offline/fallback) |
| **Embedding** | BAAI/bge-m3 (Dense, 1024-d) | Vector embedding ngữ nghĩa |
| **Sparse Embedding** | Qdrant/bm25 | Embedding thưa cho keyword matching |
| **Reranker** | BAAI/bge-reranker-v2-m3 | Cross-Encoder rerank kết quả |
| **Semantic Chunking** | paraphrase-multilingual-MiniLM-L12-v2 | Chia đoạn theo ngữ nghĩa |
| **Vector DB** | Qdrant | Lưu trữ & tìm kiếm vector (HNSW + Scalar Quantization) |
| **Cache** | Redis | Message broker (Celery) + Query cache |
| **Document Loader** | IBM Docling | Chuyển đổi tài liệu → Markdown |
| **Backend** | FastAPI + Uvicorn | REST API, async |
| **Task Queue** | Celery | Xử lý nạp tài liệu bất đồng bộ |
| **Frontend** | React 18 + Vite + TypeScript | Giao diện chat |
| **UI Components** | shadcn/ui + Radix UI + TailwindCSS | Component library |
| **Animations** | Framer Motion | Hiệu ứng giao diện |

---

## Cấu trúc thư mục

```
myEKIP/
├── app/                          # Backend chính (FastAPI)
│   ├── main.py                   # Điểm khởi tạo FastAPI app
│   ├── api/
│   │   └── routes.py             # Định nghĩa API endpoints
│   ├── core/
│   │   ├── config.py             # Cấu hình hệ thống (Pydantic Settings)
│   │   ├── cache.py              # Redis async cache (key-value)
│   │   └── querycache.py         # Semantic Cache (Qdrant-based)
│   ├── models/
│   │   └── schemas.py            # Pydantic schemas (Request/Response)
│   ├── services/
│   │   ├── embedding.py          # Hybrid Embedding (Dense + Sparse)
│   │   ├── retriever.py          # Hybrid Retriever + Reranker
│   │   ├── rag.py                # RAG orchestrator (Retrieval → LLM)
│   │   └── vectorstore.py        # Qdrant collection management
│   └── workers/
│       ├── celery_app.py         # Cấu hình Celery
│       └── ingest.py             # Task nạp tài liệu (async)
│
├── pipeline/                     # Data Ingestion Pipeline
│   ├── loaders/
│   │   ├── base.py               # Abstract BaseLoader + DocumentChunk model
│   │   ├── factory.py            # Loader Factory pattern
│   │   └── ibmDocling.py         # IBM Docling loader (PDF, DOCX, PPTX, ...)
│   └── chunkers/
│       ├── recursive.py          # Recursive Character Chunker
│       └── sematic.py            # Semantic Chunker (embedding-based)
│
├── UI/                           # Frontend (React + Vite + TypeScript)
│   └── src/
│       ├── App.tsx               # Router chính
│       ├── pages/
│       │   └── Index.tsx         # Trang chat chính
│       └── components/chat/      # Chat components
│           ├── ChatHeader.tsx
│           ├── ChatInput.tsx
│           ├── ChatMessage.tsx
│           ├── ChatSidebar.tsx
│           ├── WelcomeScreen.tsx
│           └── TypingIndicator.tsx
│
├── data/                         # Tài liệu mẫu / test
├── Uploads/                      # Thư mục lưu file upload
├── qdrant_data/                  # Dữ liệu Qdrant (Docker volume)
├── redis_data/                   # Dữ liệu Redis (Docker volume)
├── docker-compose.yml            # Qdrant + Redis containers
├── Dockerfile                    # (Đang phát triển)
├── .env                          # Biến môi trường
├── run.py                        # Entrypoint chạy Uvicorn
└── private.py                    # API key (Gemini)
```

---

## Chi tiết các thành phần

### 1. Backend API (`app/`)

#### `app/main.py` — FastAPI Application
- Khởi tạo FastAPI app với **lifespan** quản lý kết nối Redis (connect/disconnect).
- Đăng ký router từ `app/api/routes.py`.

#### `app/core/config.py` — Cấu hình trung tâm
- Sử dụng **Pydantic Settings** đọc từ file `.env`.
- Quản lý tất cả tham số: Qdrant, Redis, LLM models, RAG parameters.

#### `app/services/embedding.py` — Hybrid Embedding Service
- **Dense Embedding**: `BAAI/bge-m3` qua SentenceTransformer (1024 dimensions, cosine similarity).
- **Sparse Embedding**: `Qdrant/bm25` qua FastEmbed.
- Trả về cả 2 loại vector cho mỗi đoạn text, phục vụ hybrid search.

#### `app/services/retriever.py` — Hybrid Retriever
- **Hybrid Search** trên Qdrant sử dụng `prefetch` song song:
  - Luồng Dense: tìm kiếm theo ngữ nghĩa (semantic similarity).
  - Luồng Sparse: tìm kiếm theo từ khóa (keyword matching).
- **Fusion**: Kết hợp kết quả bằng thuật toán **RRF (Reciprocal Rank Fusion)**.
- **Reranking**: Dùng **Cross-Encoder** (`BAAI/bge-reranker-v2-m3`) để sắp xếp lại top kết quả theo độ chính xác cao hơn.
- Pipeline: Retrieve top 20 → RRF Fusion → Rerank → Lấy top 5.

#### `app/services/rag.py` — RAG Orchestrator
- Kết nối Retriever → Context Builder → LLM.
- Hỗ trợ **2 LLM**:
  - **Gemini API** (`gemini-2.5-flash-lite`): production, temperature=0.2 cho RAG chính xác.
  - **Llama-3 Local** (`meta-llama/Llama-3-8B-Instruct`): offline/fallback, FP16, device_map="auto".
- Prompt được thiết kế tiếng Việt, yêu cầu LLM chỉ trả lời dựa trên ngữ cảnh và trích dẫn nguồn.

#### `app/services/vectorstore.py` — Qdrant Management
- Tạo/quản lý Qdrant collection với cấu hình:
  - Dense vector: `COSINE` distance.
  - Sparse vector: in-memory index.
  - HNSW: `m=16`, `ef_construct=100`.
  - Quantization: `INT8 Scalar` (luôn giữ trên RAM).
- Hỗ trợ collection riêng cho Semantic Cache (`_cache`).

#### `app/core/cache.py` — Redis Async Cache
- Cache key-value truyền thống dùng SHA-256 hash.
- Async connect/disconnect quản lý bởi FastAPI lifespan.
- TTL mặc định: 3600 giây.

#### `app/core/querycache.py` — Semantic Cache
- Cache thông minh dựa trên **độ tương đồng ngữ nghĩa** (không chỉ exact match).
- Lưu vector câu query + kết quả vào Qdrant collection riêng.
- Khi có query mới, tìm kiếm hybrid trên cache → nếu score đủ cao → trả kết quả cached.

#### `app/workers/` — Celery Workers
- **Broker & Backend**: Redis.
- Task `ingest_document`: Nhận file → Load (Docling) → Chunk (Semantic) → Embed (Hybrid) → Upsert Qdrant.
- Chạy bất đồng bộ, API trả về `task_id` để theo dõi trạng thái.

---

### 2. Data Pipeline (`pipeline/`)

#### Document Loaders (`pipeline/loaders/`)
- **Factory Pattern**: Tự động chọn loader phù hợp theo file extension.
- **IBM Docling Loader**: Chuyển đổi PDF, DOCX, PPTX, XLSX, HTML → Markdown → Chia theo header Markdown.
- Hỗ trợ: `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.md`, `.html`.

#### Chunkers (`pipeline/chunkers/`)

| Chunker | Mô tả | Khi nào dùng |
|---------|--------|---------------|
| **SemanticChunker** | Chia đoạn dựa trên cosine similarity giữa các câu liền kề. Dùng model multilingual MiniLM-L12-v2. | Mặc định khi ingest |
| **RecursiveCharacterChunker** | Chia đoạn đệ quy theo separators (`\n\n` → `\n` → `. ` → ` ` → `""`). | Fallback khi SemanticChunker thất bại hoặc chunk quá lớn |

**Luồng Semantic Chunking**:
1. Tách câu bằng regex.
2. Tạo buffer context (câu xung quanh) để embedding mượt hơn.
3. Tính cosine similarity giữa câu liền kề.
4. Cắt tại vị trí similarity < threshold (0.5).
5. Nếu chunk > `chunk_size` → fallback sang RecursiveChunker.

---

### 3. Frontend UI (`UI/`)

- **Stack**: React 18 + Vite + TypeScript + TailwindCSS.
- **Component Library**: shadcn/ui (Radix UI primitives).
- **State Management**: React hooks + TanStack Query.
- **Routing**: React Router DOM.

**Giao diện Chat** gồm:
- `ChatSidebar` — Danh sách cuộc hội thoại, tạo mới, xóa.
- `ChatHeader` — Thanh điều hướng.
- `ChatInput` — Ô nhập tin nhắn.
- `ChatMessage` — Hiển thị tin nhắn (user/assistant).
- `WelcomeScreen` — Màn hình chào mừng.
- `TypingIndicator` — Hiệu ứng đang gõ.

> **Lưu ý**: Frontend hiện đang dùng **fake responses** (mock), chưa kết nối API backend.

---

### 4. Hạ tầng (Infrastructure)

#### Docker Compose
```yaml
services:
  qdrant:    # Vector DB — ports 6333, 6334
  redis:     # Cache + Broker — port 6379
```

#### Biến môi trường (`.env`)
| Biến | Giá trị mặc định | Mô tả |
|------|-------------------|-------|
| `QDRANT_HOST` | localhost | Host Qdrant |
| `QDRANT_PORT` | 6333 | Port Qdrant |
| `QDRANT_COLLECTION` | ekip_docs | Tên collection |
| `REDIS_URL` | redis://localhost:6379/0 | Redis URL |
| `LLM_MODEL_NAME` | meta-llama/Llama-3-8B-Instruct | Model LLM local |
| `EMBEDDING_MODEL` | BAAI/bge-m3 | Model embedding |
| `RERANKER_MODEL` | BAAI/bge-reranker-v2-m3 | Model reranker |
| `CHUNK_SIZE` | 512 | Kích thước chunk |
| `CHUNK_OVERLAP` | 64 | Overlap giữa chunks |
| `TOP_K_RETRIEVE` | 20 | Số lượng retrieve |
| `TOP_K_RERANK` | 5 | Số lượng sau rerank |

---

## Luồng xử lý dữ liệu

### Luồng Ingest (Nạp tài liệu)
```
Upload File → API /ingest
    → Celery Task (async)
        → IBM Docling: File → Markdown
        → Markdown Header Splitter
        → Semantic Chunker (+ Recursive fallback)
        → BGE-M3 Dense + BM25 Sparse Embedding
        → Upsert vào Qdrant (ekip_docs collection)
    → Trả task_id → Theo dõi qua /ingest/status/{task_id}
```

### Luồng Query (Truy vấn)
```
User Query → API /query
    → [Bước 0] Semantic Cache check (Qdrant cache collection)
        → Cache HIT → Trả kết quả ngay
        → Cache MISS ↓
    → [Bước 1] Hybrid Embedding (Dense + Sparse)
    → [Bước 2] Qdrant Hybrid Search
        → Prefetch Dense (top 20)
        → Prefetch Sparse (top 20)
        → RRF Fusion (top 20)
    → [Bước 3] Cross-Encoder Rerank → Top 5
    → [Bước 4] Build Context (ghép tài liệu + nguồn)
    → [Bước 5] Gemini API → Sinh câu trả lời
    → [Bước 6] Lưu vào Semantic Cache
    → Trả Response (answer + sources + cached flag)
```

---

## API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/api/v1/health` | Kiểm tra sức khỏe hệ thống (API, Qdrant, Redis) |
| `POST` | `/api/v1/ingest` | Upload tài liệu để nạp (multipart/form-data) |
| `GET` | `/api/v1/ingest/status/{task_id}` | Kiểm tra trạng thái nạp tài liệu |
| `POST` | `/api/v1/query` | Truy vấn RAG (JSON body) |

### Ví dụ Query Request
```json
{
  "query": "Vector database là gì?",
  "top_k": 5,
  "use_cache": true,
  "stream": false
}
```

### Ví dụ Query Response
```json
{
  "answer": "Vector database là cơ sở dữ liệu...",
  "sources": [
    {
      "text": "Nội dung tài liệu...",
      "metadata": { "source": "document.pdf" },
      "score": 0.95
    }
  ],
  "cached": false
}
```

---

## Cách khởi chạy

### 1. Khởi động hạ tầng (Qdrant + Redis)
```bash
docker-compose up -d
```

### 2. Khởi động Celery Worker (terminal riêng)
```bash
celery -A app.workers.celery_app worker --loglevel=info -P solo
```

### 3. Khởi động Backend API
```bash
python -m run
```
> API chạy tại `http://0.0.0.0:8000` — Swagger docs tại `http://localhost:8000/docs`

### 4. Khởi động Frontend (tuỳ chọn)
```bash
cd UI
npm install
npm run dev
```

---

## Cấu hình

Toàn bộ cấu hình được quản lý qua file `.env` tại thư mục gốc.  
Lớp `Settings` trong `app/core/config.py` sử dụng **Pydantic Settings** để load và validate.

---

*Phiên bản: 2.0 | Cập nhật: 04/03/2026*