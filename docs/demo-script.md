# Demo script (Task 5 — Complete assistant)

Target length: 2–3 minutes. Record a wide viewport.

1. **Open the app** — local `http://localhost:3000` or the deployed URL. AI service must be reachable.
2. **Overview** — one product: workspace, chat, documents, tools, Prompt Lab.
3. **Open `/workspace`**. Point at conversation history, the chat, and the documents panel.
4. **Upload** a small synthetic PDF. Wait until **Ready for search**.
5. **Ask a document question** the PDF can answer.
   - Status: **Searching uploaded documents**
   - Sources show `Filename.pdf, p. N` (not web links)
6. **New chat**, then ask `What is 12 * (3 + 4)?`
   - Status: **Using calculator**
   - Result **84**
   - Sidebar title updates from the question
7. **Ask** `What's the weather in Paris?` or `Search the web for retrieval-augmented generation`.
   - Status names the tool
   - Label **External tool** / **Web sources (external)** — not document citations
8. **Optional 15s** — `/prompt-lab` on the same question across five strategies. Structured card shows parsed fields only.
9. **Close** with: one assistant, grounded documents, labeled tools, history, and a Docker path to run it.

If the live host is not ready, record Docker Compose locally (`docker compose up --build`) and say the same images are what you deploy.
