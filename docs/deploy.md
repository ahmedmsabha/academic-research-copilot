# Deploy

Production target: **Vercel** for `apps/web`, **Hugging Face Gradio Space** (free, no credit card) for `apps/ai-service`, **Prisma Postgres** (pgvector) for the database.

Hugging Face **Docker** Spaces are paid. **Gradio** Spaces are free. The Space still runs FastAPI: Gradio is only the free runtime. The Vercel app calls `/health` and `/api/v1` on the Space URL.

Secrets stay server-side. Never put API keys or `DATABASE_URL` in `NEXT_PUBLIC_*` variables.

```text
Browser  →  Vercel (Next.js)  →  Hugging Face Gradio Space (FastAPI + status page)
                                      │
                                      └─ Prisma Postgres + pgvector
```

Free Spaces sleep when idle. The first request after sleep can take about a minute. Uploaded PDF files on the Space disk can disappear after a restart; chat history and embeddings stay in Prisma Postgres. Re-upload a demo PDF if search stops finding the file.

## 0. Prerequisites

- [Vercel](https://vercel.com) account connected to GitHub
- [Hugging Face](https://huggingface.co/join) account (free, no card)
- Existing Prisma Postgres URL (`DATABASE_URL`) with the `vector` extension
- `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/apikey)

Apply migrations to the **same** database the AI service will use:

```bash
cd apps/web
npx prisma migrate deploy
```

## 1. Hugging Face Space — AI service (Gradio, free)

1. Open [huggingface.co/new-space](https://huggingface.co/new-space).
2. Create the Space:

   | Field | Value |
   |---|---|
   | Space name | `academic-research-copilot-ai` (or any free name) |
   | SDK | **Gradio** (not Docker — Docker is paid) |
   | Hardware | **CPU basic** (free) |
   | Visibility | Public (so the Vercel app can call it) |

   If the wizard asks for a Gradio template, pick a blank / default one. We overwrite the files in step 4.

3. Space settings → **Variables and secrets** → add **secrets**:

```text
APP_ENV=production
GEMINI_API_KEY=your-gemini-key
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/postgres?sslmode=require
CORS_ORIGINS=https://your-app.vercel.app
STORAGE_PROVIDER=local
STORAGE_LOCAL_ROOT=/data/uploads
DEV_FAKE_LLM=false
DEV_FAKE_EMBEDDINGS=false
```

You can set `CORS_ORIGINS` to a placeholder and fix it after Vercel is live. No trailing slash.

4. Upload **only** `apps/ai-service` (the Space root must contain `app.py`, `requirements.txt`, and `app/`):

```bash
pip install -U huggingface_hub
huggingface-cli login
cd apps/ai-service
huggingface-cli upload YOUR_HF_USERNAME/academic-research-copilot-ai . . --repo-type space
```

5. Wait until the Space is **Running**. Then:

```bash
curl https://YOUR_HF_USERNAME-academic-research-copilot-ai.hf.space/health
# {"status":"ok","service":"ai-service"}
```

The public API host is `https://<user>-<space>.hf.space`. The Gradio status page is the Space UI; the API is on the same host. If health fails, open the Space **Logs** tab.

## 2. Vercel — web app

1. [vercel.com](https://vercel.com) → **Add New… → Project** → import `ahmedmsabha/academic-research-copilot`.
2. **Root Directory:** `apps/web`. Framework: Next.js.
3. Environment variable (Production and Preview):

```text
NEXT_PUBLIC_API_BASE_URL=https://YOUR_HF_USERNAME-academic-research-copilot-ai.hf.space
```

That value is public (API origin, not a secret). It is inlined at build time — change it, then redeploy.

4. Deploy. Your site will be `https://<project>.vercel.app`.

## 3. Wire CORS

In the Space **Secrets**, set:

```text
CORS_ORIGINS=https://<project>.vercel.app
```

Restart the Space if it does not pick up the change. Then open `/workspace` and send a message.

## 4. Smoke test

1. Open `https://<project>.vercel.app/workspace` (wait if the Space is waking up).
2. Upload a small synthetic PDF and wait until **Ready for search**.
3. Ask a document question, `What is 12 * (3 + 4)?`, and a weather or web-search question.
4. Confirm filename/page citations and **External tool** labels.

## Local Docker Compose (unchanged)

```bash
cp .env.example .env
# Set GEMINI_API_KEY
docker compose up --build
```

## After it is live

Put the Vercel URL in the README and LinkedIn draft.

Identity is still the development `X-User-Id` header (browser localStorage). Treat a public demo as shared-device scoped, not multi-tenant production auth.
