# Task 2 interview study guide

Academic Research Copilot — RAG. Memorize the pitch, then the two pipelines (index, then retrieve+answer), then the “why” behind citations, isolation, and insufficient evidence. Task 1 is the chat spine. Task 3 tools and Task 4 Prompt Lab sit elsewhere.

> **30-second pitch — say this first**
>
> I built a RAG pipeline for academic PDFs. The browser never talks to Gemini or pgvector. FastAPI extracts page-aware text, chunks it, embeds with Gemini, and stores vectors in PostgreSQL. On a question, we retrieve project-scoped chunks, generate an answer only from that context, and attach citations from retrieval metadata — never from free-form model text. If scores are weak, we say the documents do not contain enough information.

| | |
|---|---|
| `/rag` | Task 2 demo page |
| `mode=rag` | Pinned route |
| `768-d` | gemini-embedding-001 |
| pgvector | Cosine distance search |

## What Task 2 is (and is not)

| Requirement | What this app does | Do not claim in Task 2 |
|---|---|---|
| Extract text from PDFs | PyMuPDF, page-aware, `%PDF-` magic bytes; empty text layer falls back to Tesseract OCR | Cloud Vision / Gemini page-image OCR |
| Split into chunks | 800 chars, 150 overlap, break on whitespace, keep `page_start`/`page_end` | Recursive markdown splitters or heading parsers |
| Generate embeddings | `GeminiEmbeddingProvider`, 768 dims, batched with retries | OpenAI text-embedding-3, client-side embeddings |
| Store in a vector DB | PostgreSQL pgvector column on `document_chunks` | Pinecone / Chroma / FAISS as the production store |
| Retrieve relevant chunks | Project-scoped cosine distance, `top_k=5`, dual thresholds, overview hybrid | Hybrid BM25 + reranker (not implemented) |
| Context-aware answers | `RAG_SYSTEM_INSTRUCTION` + retrieved excerpts only; citations from metadata | The model invents `Filename.pdf, p. 4` from memory |

## Two pipelines you must be able to draw

Interviewers will ask you to whiteboard RAG. Draw indexing first, then query time. They are not the same request.

### Pipeline A — index (upload)

Browser `DocumentPanel` → POST multipart `/api/v1/projects/{id}/documents` → FastAPI `upload_document` → validate → `LocalObjectStorage.put_pdf` → row `status=queued` → `BackgroundTasks` index → extracting → chunking → embedding → indexing → ready.

| Step | Layer | File | What happens |
|---|---|---|---|
| 1 | UI | `DocumentPanel.tsx` | PDF-only input. Client also rejects non-`.pdf` names. Disabled while uploading. |
| 2 | Proxy | `app/api/v1/[...path]` | Same-origin Next proxy. Secrets stay on FastAPI. |
| 3 | Validate | `documents.py` `_validate_upload` | Non-empty, max 20 MiB, `.pdf` or MIME, then `looks_like_pdf` (`%PDF-`). |
| 4 | Store bytes | `providers/storage.py` | Key is server-made: `{userId}/{projectId}/{documentId}.pdf`. Filename is display-only. |
| 5 | Row | `postgres_store.py` | Document record queued with sha256 checksum. PDF bytes are not in Postgres. |
| 6 | Extract | `rag/extract.py` | PyMuPDF `page.get_text`. One-based page numbers. Near-empty (&lt;40 chars) → Tesseract `get_textpage_ocr`, then fail if still empty. |
| 7 | Chunk | `rag/chunking.py` | 800/150, prefer whitespace breaks, each chunk carries page range + char offsets. |
| 8 | Embed | `providers/embeddings.py` | `gemini-embedding-001`, `output_dimensionality=768`. Batch size 1, pause, retries. |
| 9 | Index | `replace_chunks` | Delete old chunks for that document, insert new ones. Retry is idempotent. |
| 10 | UI poll | `DocumentPanel.tsx` | Every 2s while status is queued/extracting/chunking/embedding/indexing. |

### Pipeline B — query (grounded chat)

`ChatPanel` `mode=rag` → POST `/conversations/{id}/messages` `{ content, mode: rag }` → `ChatService.send_message` → `select_route` pins rag → `_answer_with_rag` → embed question → `search_chunks` → `build_context_block` + `citations_from_chunks` → Gemini with `RAG_SYSTEM_INSTRUCTION` → persist answer + citation JSON.

| Step | Layer | File | What happens |
|---|---|---|---|
| 1 | UI | `app/rag/page.tsx` | `ChatPanel mode="rag"` `showDocuments`. Loading status: Searching uploaded documents. |
| 2 | Route pin | `agent/router.py` | `preferred=rag` short-circuits. No calculator, weather, or web search on `/rag`. |
| 3 | Ready check | `ChatService.send_message` | No ready docs → assistant says upload/wait. Still HTTP 201, `route=rag`, no citations. |
| 4 | Query vector | `GeminiEmbeddingProvider` | Same model and dimension as stored chunks. Incompatible vectors are never mixed. |
| 5 | Retrieve | `postgres_store.search_chunks` | Filter `project_id` + `status=ready` + model + dim. Cosine distance ≤ threshold. `top_k=5`. |
| 6 | Overview fork | `rag/retrieval.py` | “Summarize this paper” uses early ordinal chunks + semantic, merged to 10. |
| 7 | Threshold | `config.py` | Strict 0.55, then relaxed 0.78. Empty after both → insufficient evidence. |
| 8 | Citations | `rag/citations.py` | Built in application code from `RetrievedChunk`. Deduped by document+page range. |
| 9 | Generate | `ChatService._answer_with_rag` | Prompt = excerpts + question. System: answer only from context. Treat excerpts as untrusted. |
| 10 | UI | `MessageList.tsx` | Footer “Document sources” renders `citation.label` from the API. Never parses the prose. |

## State machine — recite this

`uploaded → queued → extracting → chunking → embedding → indexing → ready`, or any processing state can go to `failed`. Only `status=ready` chunks enter search. The UI never implies a PDF is searchable until Ready for search.

| Status | Meaning | User sees |
|---|---|---|
| `queued` | Bytes stored; indexing not started or reset for retry | Queued |
| `extracting` | Reading PDF from storage, PyMuPDF | Extracting text |
| `chunking` | Splitting extracted pages | Chunking |
| `embedding` | Calling Gemini `embed_content` | Embedding |
| `indexing` | Writing chunk rows + vectors | Indexing |
| `ready` | Searchable | Ready for search |
| `failed` | Safe `failure_code` + `failure_message`; chunks deleted | Indexing failed + Retry |

> **Tests vs production timing**
>
> In `APP_ENV=test`, upload indexes synchronously so pytest can assert `status=ready` on the 201. In development/production, the 201 returns `queued` and FastAPI `BackgroundTasks` runs `_index_in_background` with a fresh DB session. That is not a Celery/RQ worker — own that if asked.

## Architecture decisions — say the “why”

### Why RAG at all

Gemini’s weights do not contain the user’s PDF. Stuffing the whole file blows the context window and mixes irrelevant pages. Retrieve a few relevant chunks, then generate. Grounding is a product rule, not a prompt hope.

### Why citations come from metadata

Models hallucinate “Smith 2021, p. 12”. `citations_from_chunks` maps real `RetrievedChunk` rows to `CitationResponse`. The UI prints `label`. We never regex the assistant prose for filenames.

### Why pgvector in Postgres

One database for projects, documents, messages, and vectors. Retrieval can JOIN documents and filter `status=ready` in the same query. Prisma owns migrations; SQLAlchemy queries `Vector(768)` because Prisma Client cannot.

### Why filter model + dimension

Cosine on mixed embedding spaces is meaningless. `search_chunks` requires `embedding_model` and `embedding_dimension` to match the query vector. Changing models needs a re-index, not a silent mix.

### Why overlap = 150

A claim that straddles an 800-char cut would be split in half. Overlap keeps boundary sentences in two chunks so retrieval can still hit them. Chunker also prefers whitespace so we do not cut mid-word.

### Why excerpts are “untrusted evidence”

PDFs can contain “ignore previous instructions”. `RAG_SYSTEM_INSTRUCTION` says excerpts are evidence, not commands. The agent must not gain tools, leak secrets, or leave the project because a paper asked it to.

## Retrieval math — they will quiz this

The store ranks by cosine **distance**, not cosine similarity. `distance = 1 − similarity`. Lower is better. `RETRIEVAL_MAX_DISTANCE=0.55` means similarity at least about 0.45. If nothing passes, we retry at 0.78 (~0.22 similarity). Still nothing → canned insufficient-evidence reply, `citations=[]`.

| Knob | Default | Why |
|---|---|---|
| `CHUNK_SIZE_CHARS` | 800 | Fits several sentences; not a whole chapter |
| `CHUNK_OVERLAP_CHARS` | 150 | Boundary continuity |
| `RETRIEVAL_TOP_K` | 5 | AGENTS.md target 4–6 |
| `RETRIEVAL_MAX_DISTANCE` | 0.55 | Strict gate so weak neighbors do not become “facts” |
| `RETRIEVAL_RELAXED_MAX_DISTANCE` | 0.78 | Second chance before refusing |
| `EMBEDDING_DIMENSION` | 768 | `gemini-embedding-001` `output_dimensionality`; pgvector `vector(768)` |
| `EMBEDDING_BATCH_SIZE` | 1 | Gemini free-tier quota; lock + pause + up to 8 retries |

> **Overview queries are a special case**
>
> “Summarize this paper” shares almost no tokens with methods/tables. Pure similarity often ranks the bibliography. `is_document_overview_query` detects summarize/overview/main findings. We take early ordinal chunks (title, abstract, intro) and merge unique semantic hits, cap 10. Prompt asks for a grounded summary and forbids inventing missing sections.

## Project isolation and delete

| Rule | How it is enforced |
|---|---|
| Owner + project on every query | `get_document` / `list_documents` / `search_chunks` all filter `project_id`. Search also joins `DocumentRow.status == ready`. |
| Other user’s document | 404 Document not found — same 404-not-403 policy as Task 1 conversations. |
| Object key | Generated server-side. Display filename is sanitized; never used as the storage path. |
| Delete | DB document + chunks (Prisma `onDelete Cascade` / `store.delete_document`) then `storage.delete_object`. 204. |
| After delete | `test_delete_removes_from_retrieval`: no ready docs left, `ChatService` falls back to `route=llm` on auto. On `/rag` the pin still says rag and tells you to upload. |
| Retry | `queue_document_retry` clears failure, deletes chunks, sets queued. Mid-pipeline statuses are not double-started. |

## Error handling — codes to recite

| HTTP | code | When |
|---|---|---|
| 201 | (success) | Upload accepted. Test env may already be ready; prod is queued. |
| 204 | (no body) | Delete succeeded |
| 400 | `VALIDATION_ERROR` | Empty file |
| 404 | `NOT_FOUND` | Project or document not owned / missing |
| 409 | `DOCUMENT_LIMIT` | More than 20 documents in the project |
| 413 | `DOCUMENT_TOO_LARGE` | Over `MAX_UPLOAD_BYTES` (20 MiB) |
| 415 | `UNSUPPORTED_DOCUMENT` | Not a PDF by name/MIME or missing `%PDF-` |
| 422 | `DOCUMENT_PROCESSING_ERROR` | Empty extract, chunk failure, embed mismatch — also stored on the row |
| 503 | `PROVIDER_UNAVAILABLE` | Embedding quota / empty vectors |
| 504 | `PROVIDER_TIMEOUT` | Embedding deadline |

> **Insufficient evidence is not a 422**
>
> `InsufficientEvidenceError` exists in `errors.py` but the chat path does not raise it. `_persist_insufficient` returns HTTP 201 with a fixed assistant sentence, `route=rag`, `citations=[]`. Same idea for “no ready documents.” Chat stays a conversation, not an error banner. Do not say “we throw `INSUFFICIENT_EVIDENCE`.”

## UI behavior to demo live

| State | What the interviewer should see |
|---|---|
| Empty documents | No documents yet — upload a PDF to enable grounded answers |
| Uploading | Uploading and queuing for indexing…; input disabled |
| Indexing | Extracting text / Chunking / Embedding / Indexing…; 2s poll; sr-only live status |
| Ready | Ready for search + page count + size + date |
| Failed | Indexing failed, `failure_message`, Retry button |
| Delete | `window.confirm`; then row gone |
| Chat empty | Ask about your documents |
| Sending | Searching uploaded documents |
| Hit | Answer + Document sources: `notes.pdf, p. 1` |
| Miss | “…do not contain enough information…” and no source footer |

## Drill these questions

### Walk me through RAG from upload to citation

User uploads a PDF. We validate signature and size, store bytes under a server-generated key, insert a queued document. Background indexing extracts pages, chunks ~800/150, embeds with Gemini 768-d, replaces chunks in pgvector. User asks a question on `/rag`. We pin route rag, embed the question with the same model, search cosine distance within the project among ready docs, build a labeled context block, call Gemini with a strict grounded system prompt, and attach `CitationResponse` objects from the retrieved rows. The UI prints those labels.

### How do you stop the model from inventing citations?

Three layers. Retrieval is the only source of `document_id`, filename, and pages. `citations_from_chunks` runs in Python, not in the model. The system prompt forbids inventing filenames or pages. The frontend never parses the answer for sources — it only renders `message.citations` from the API.

### What is an embedding?

A list of 768 floats that places text in a space where related meaning is nearby. We embed each chunk at index time and the user question at query time with the same model. Ranking uses cosine distance on those vectors — not keyword count. `FakeEmbeddingProvider` hashes tokens into a unit vector so tests stay deterministic and free.

### Why chunk instead of embedding the whole PDF?

Retrieval needs a unit of evidence that can be cited to a page. A 40-page paper as one vector averages title, methods, and references together. Small overlapping chunks let us return `notes.pdf, pp. 4–5` and keep the LLM context small and on-topic.

### How is this different from Task 1 chat?

Task 1 sends last 40 turns with a general system prompt. Task 2 on `/rag` does not send conversation history to Gemini — only the current question plus retrieved excerpts and `RAG_SYSTEM_INSTRUCTION`. Status is Searching uploaded documents. `DocumentPanel` is on this page. `/chat` still pins llm and must not retrieve.

### What happens if the PDF is scanned?

PyMuPDF `get_text` returns almost nothing. `is_near_empty` if total chars &lt; 40. We then call `page.get_textpage_ocr` (Tesseract on PATH, `ENABLE_OCR=true`). If Tesseract is missing, fail with a retryable message. If OCR still yields &lt;40 chars, fail honestly. Chunks from a failed run are deleted. Do not claim Gemini/Vision OCR.

### How do you test without paying Google?

`conftest` injects `FakeEmbeddingProvider` and `FakeLLMProvider`. `make_text_pdf` builds tiny PyMuPDF fixtures. `test_rag_answer_includes_citation` asserts route, status, filename, `page_start`, and that the LLM prompt contained Document excerpts. `test_insufficient_evidence_is_honest` uses unrelated Mars/ACME questions against a photosynthesis PDF. Isolation and delete tests are in the same file.

### How would you improve this if you had another week?

Honest next steps: a real worker queue instead of `BackgroundTasks`, hybrid lexical+vector search, a reranker, signed PDF open from a citation, pass a short conversation summary into the grounded prompt, and transactional storage cleanup if object delete fails after the DB row is gone. Do not invent a reranker you did not ship.

## If they ask “was this AI-generated?”

> **Do not deny it. Own the architecture.**
>
> I used AI to move faster on boilerplate, but I can defend the RAG boundaries: citations are built from retrieved rows, answers in document mode may not use model trivia, vectors are project-scoped, empty PDFs fail without fake text, and `/rag` pins mode so the agent cannot silently web-search. Then walk Pipeline A and Pipeline B. That is what they are testing — comprehension, not who typed `chunking.py`.

### Phrases that sound like you built it

| Say | Avoid |
|---|---|
| Citations are assembled in `citations.py` from `RetrievedChunk`, not from the model’s prose. | The AI cites the PDF. (how?) |
| We store cosine distance and refuse below 0.55, then 0.78, then we tell the user we lack evidence. | It always finds the relevant page. |
| pgvector lives in Postgres; Prisma migrates `vector(768)`; SQLAlchemy runs `cosine_distance`. | We use a vector database. (which one?) |
| `/rag` pins `mode=rag` so Task 3 tools cannot hijack the demo. | The assistant automatically uses documents. (that is auto routing, Task 5) |
| Object keys are `user/project/uuid.pdf`. The original filename is display-only. | We save the file as the user’s filename on disk. |
| `FakeEmbeddingProvider` is a hashed bag-of-tokens unit vector for pytest. | I tested it by uploading a paper. (they want automated tests) |

## Honest limitations (better than getting caught)

| Limitation | Accurate sentence |
|---|---|
| OCR quality | Tesseract English fallback when the PDF has no text layer. Poor scans can still fail. |
| Storage | `LocalObjectStorage` under `.data/uploads`. R2/Supabase are architecture targets, not this deployment. |
| Indexing job | FastAPI `BackgroundTasks` plus a new SQLAlchemy session — not a durable worker. Process restart can drop an in-flight job. |
| RAG history | Grounded generate uses the current question + excerpts, not the last 40 chat turns. |
| No reranker | Single-stage cosine top-k. Overview questions add leading-page bias because similarity alone was weak. |
| Citation click-through | Labels only. No authorized signed URL to open the PDF at that page yet. |
| Delete cleanup | DB delete commits first. If `storage.delete_object` fails, we log it; the object can orphan. |
| Unused error classes | `InsufficientEvidenceError` and `DocumentNotReadyError` are defined but chat returns 201 with a message instead. |
| Auth | Same as Task 1: `X-User-Id`, not OAuth. |
| Quota | Embed batch size 1, 1.5s pause, lock, retries — a free-tier workaround, not a production ingest design. |

## Live demo (about 2 minutes)

Open `/rag`. Upload a short text PDF (not a scan). Wait until Ready for search. Ask a question whose words appear in the file — point at Document sources: filename, p. N. Ask something the PDF cannot answer — show the insufficient evidence sentence and no source footer. Optionally delete the PDF and ask again to show “no ready documents.” Do not use weather, calculator, or Prompt Lab on this page if you are presenting Task 2.

## Re-read the night before

### Must-read files

- `apps/web/app/rag/page.tsx` — `mode=rag`
- `apps/web/features/documents/DocumentPanel.tsx`
- `apps/ai-service/app/services/documents.py` — `_run_pipeline`
- `apps/ai-service/app/rag/extract.py` / `chunking.py` / `citations.py`
- `apps/ai-service/app/services/chat.py` — `_answer_with_rag`
- `apps/ai-service/app/repositories/postgres_store.py` — `search_chunks`
- `apps/ai-service/app/providers/embeddings.py`
- `apps/ai-service/tests/integration/test_rag_api.py`

### Numbers to remember

- Chunk 800 / overlap 150
- `top_k` = 5 (overview merge cap 10)
- Distance 0.55 then 0.78
- 768-d `gemini-embedding-001`
- Upload max 20 MiB, 20 docs/project
- Empty PDF threshold: 40 characters
- Poll every 2 seconds
- Status: Searching uploaded documents
- Citation: `filename.pdf, p. 4` or `pp. 4–5`

---

Source: this repository’s Task 2 path as it exists after Tasks 3–5 were added. `/rag` still pins rag. `ChatService` also contains tools — skip those unless asked how grounded mode coexists with the agent.
