# Demo script (Task 2 — RAG)

Target length: 2–3 minutes.

1. **Open the app** (`http://localhost:3000`) with the AI service running on port 8000.
2. **Show empty documents panel** — “No documents yet.”
3. **Upload a short academic PDF** (a public/sample notes PDF with clear page text). Point out indexing status moving to **Ready for search**.
4. **Ask a grounded question** that the PDF can answer. Show:
   - status “Searching uploaded documents”
   - answer grounded in the PDF
   - citation like `Filename.pdf, p. N`
5. **Ask an off-topic question** and show the honest insufficient-evidence reply (no fake citations).
6. **Delete the document**, confirm the dialog, then ask again — chat falls back to general LLM mode without document citations.
7. **Close** with: project isolation, pgvector embeddings, and citations built from retrieval metadata—not invented by the model.

Recording tip: keep the documents panel and chat visible together on a wide viewport.
