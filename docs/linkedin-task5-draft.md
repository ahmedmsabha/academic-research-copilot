# LinkedIn draft — Task 5: Complete AI Assistant

I just shipped Task 5 of Academic Research Copilot: a complete research assistant that combines chat, PDF RAG, tool calling, and Prompt Lab in one deployable product.

**Problem**  
Earlier tasks proved each capability in isolation. A portfolio assistant is only complete when those pieces share one workspace, one history, honest errors, and a path to run online.

**What I built**
- Unified `/workspace`: conversation history, PDF panel, and auto tool/RAG routing
- Persistent chats that retitle from the first question
- Docker Compose: Next.js, FastAPI, PostgreSQL + pgvector, health checks, named volumes
- Production startup checks (no fake providers, required secrets)
- CI for lint and tests on both apps

**Technologies used:** Next.js, FastAPI, Google Gemini, Prisma Postgres, pgvector, Docker, constrained agent routing, versioned prompt templates.

**Challenges**
- Combining features without breaking Task 1–4 demo pages or citation rules
- Making Docker use a local pgvector database while keeping Prisma migrations as the schema source of truth
- Keeping deploy docs honest: the live URL is added after the host is actually up

**Lesson**  
A complete AI assistant is an integration problem: identity, project isolation, storage, routing, and UI states have to agree — the model call is the easy part.

GitHub: https://github.com/ahmedmsabha/academic-research-copilot  
Live app: add URL after deploy (see docs/deploy.md)  
Demo: record from docs/demo-script.md

#AI #LLM #RAG #FastAPI #NextJS #Docker #BuildInPublic
