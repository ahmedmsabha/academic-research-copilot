# Deploy

Production target: **two Vercel Hobby projects** from this one GitHub repo, plus **Prisma Postgres** (pgvector).

Railway / Render / Fly hobby plans need a card or run out of credit. Vercel Hobby is free, supports FastAPI, and allows more than one project per repo. You do not need a second hosting company.

Secrets stay server-side. Never put API keys or `DATABASE_URL` in `NEXT_PUBLIC_*` variables.

```text
Browser  →  Vercel project “web” (Next.js, apps/web)
                │
                │  NEXT_PUBLIC_API_BASE_URL
                ▼
         Vercel project “ai” (FastAPI, apps/ai-service)
                │
                └─ Prisma Postgres + pgvector
```

## 0. Prerequisites

- [Vercel](https://vercel.com) account connected to GitHub (Hobby is enough)
- Existing Prisma Postgres URL (`DATABASE_URL`) with the `vector` extension
- `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/apikey)

Apply migrations to the **same** database the AI service will use:

```bash
cd apps/web
npx prisma migrate deploy
```

## 1. Vercel — AI service (backend)

This is a **second Vercel project**, not a second GitHub repo.

1. [vercel.com](https://vercel.com) → **Add New… → Project** → import `academic-research-copilot`.
2. **Root Directory:** `apps/ai-service`.
3. Framework should detect **FastAPI** / Python. If it asks, leave the build command empty.
4. Environment variables (Production and Preview):

```text
APP_ENV=production
GEMINI_API_KEY=your-gemini-key
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/postgres?sslmode=require
CORS_ORIGINS=https://your-web.vercel.app
STORAGE_PROVIDER=local
STORAGE_LOCAL_ROOT=/tmp/uploads
DEV_FAKE_LLM=false
DEV_FAKE_EMBEDDINGS=false
```

Use `/tmp/uploads` on Vercel (the function disk is ephemeral). Keep Prisma Postgres — do not add a Vercel Postgres. You can fix `CORS_ORIGINS` after the web project exists. No trailing slash.

5. Deploy. The URL looks like `https://academic-research-copilot-ai.vercel.app`.

6. Check:

```bash
curl https://<ai-project>.vercel.app/health
# {"status":"ok","service":"ai-service"}
```

`apps/ai-service/app/main.py` already exports `app`. `vercel.json` sets a 300s Hobby function limit so Gemini + RAG can finish.

Vercel serverless request bodies are smaller than a VPS (about 4.5 MB). Use a small synthetic PDF for the live demo.

## 2. Vercel — web app

1. **Add New… → Project** again → the **same** GitHub repo.
2. **Root Directory:** `apps/web`. Framework: Next.js.
3. Environment variable (Production and Preview):

```text
NEXT_PUBLIC_API_BASE_URL=https://<ai-project>.vercel.app
```

That value is public (API origin, not a secret). It is inlined at build time — change it, then redeploy.

4. Deploy. Your site will be `https://<web-project>.vercel.app`.

## 3. Wire CORS

In the **AI** Vercel project → Settings → Environment Variables, set:

```text
CORS_ORIGINS=https://<web-project>.vercel.app
```

Redeploy the AI project (or restart) so it picks up the value. Then open `/workspace` and send a message.

## 4. Smoke test

1. Open `https://<web-project>.vercel.app/workspace`.
2. Upload a **small** synthetic PDF and wait until **Ready for search**.
3. Ask a document question, `What is 12 * (3 + 4)?`, and a weather or web-search question.
4. Confirm filename/page citations and **External tool** labels.

Uploaded PDF bytes can disappear when the function instance is replaced. Chat history and embeddings stay in Prisma Postgres. Re-upload the demo PDF if search stops finding the file.

## Local Docker Compose (unchanged)

```bash
cp .env.example .env
# Set GEMINI_API_KEY
docker compose up --build
```

## After it is live

Put the **web** Vercel URL in the README and LinkedIn draft.

Identity is still the development `X-User-Id` header (browser localStorage). Treat a public demo as shared-device scoped, not multi-tenant production auth.
