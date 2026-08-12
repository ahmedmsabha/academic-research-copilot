# LinkedIn draft — Task 2: RAG System

I just shipped Task 2 of Academic Research Copilot: a retrieval-augmented generation pipeline for academic PDFs.

**Problem**  
Students and researchers need answers grounded in *their* readings—not generic model memory, and not invented citations.

**What I built**
- PDF upload with validation and indexing status
- Page-aware extraction + chunking
- Gemini embeddings stored in PostgreSQL/pgvector
- Project-scoped retrieval and grounded chat answers
- Citations with filename and page number from real retrieved chunks
- Honest “insufficient evidence” responses when the documents don’t cover the question

**Technologies used:** Next.js, FastAPI, Prisma Postgres + pgvector, Google Gemini (`gemini-embedding-001` + chat model), PyMuPDF.

**Challenges**
- Keeping citations honest (build them from retrieval metadata, never from free-form model text)
- Isolating documents and vectors per project/user
- Handling empty/scanned PDFs and indexing failures safely

**Lesson**  
RAG quality is as much product discipline as model choice: validation, status UX, thresholds, and refusal to fabricate sources matter as much as the embedding call.

GitHub: https://github.com/ahmedmsabha/academic-research-copilot  
Screenshots: docs/screenshots/task2-*.png  
Demo: record from docs/demo-script.md (add video link after publishing)

#AI #RAG #FastAPI #NextJS #pgvector #Gemini #BuildInPublic
