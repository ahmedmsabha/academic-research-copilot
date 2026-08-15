# Deploy

Production target: **Vercel** for `apps/web`, **Render** (free) for `apps/ai-service`, **Prisma Postgres** (pgvector) for the database.

No Fly.io CLI. Railway is a paid/trial host — use Render’s free web service instead.

Secrets stay server-side. Never put API keys or `DATABASE_URL` in `NEXT_PUBLIC_*` variables.

```text
Browser  →  Vercel (Next.js)  →  Render (FastAPI, free)
                                      │
                                      └─ Prisma Postgres + pgvector
```

Free Render instances sleep after idle time. The first request after sleep can take ~30–60 seconds. Uploaded PDF files live on the instance disk and can disappear after a sleep or redeploy; chat history and embeddings stay in Prisma Postgres. Re-upload a demo PDF if search stops finding the file.

## 0. Prerequisites

- [Vercel](https://vercel.com) account connected to GitHub
- [Render](https://render.com) account connected to GitHub
- Existing Prisma Postgres URL (`DATABASE_URL`) with the `vector` extension
- `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/apikey)

Apply migrations to the **same** database the AI service will use:

```bash
cd apps/web
npx prisma migrate deploy
```

## 1. Render — AI service (free)

1. Open [dashboard.render.com](https://dashboard.render.com) → **New → Web Service**.
2. Connect `ahmedmsabha/academic-research-copilot`.
3. Settings:

   | Field | Value |
   |---|---|
   | Root Directory | `apps/ai-service` |
   | Runtime | Docker |
   | Instance type | **Free** |
   | Health check path | `/health` |

4. Environment variables:

```text
APP_ENV=production
STORAGE_PROVIDER=local
STORAGE_LOCAL_ROOT=/data/uploads
DEV_FAKE_LLM=false
DEV_FAKE_EMBEDDINGS=false
GEMINI_API_KEY=your-gemini-key
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/postgres?sslmode=require
CORS_ORIGINS=https://your-app.vercel.app
```

You can set `CORS_ORIGINS` to a placeholder and fix it after Vercel is live. No trailing slash.

5. Deploy. The URL looks like `https://academic-research-copilot-ai.onrender.com`.

6. After the first deploy finishes (it can take several minutes):

```bash
curl https://<service>.onrender.com/health
# {"status":"ok","service":"ai-service"}
```

If that fails, open the service **Logs** on Render. A missing `GEMINI_API_KEY` or `DATABASE_URL` stops production startup.

Alternatively, **New → Blueprint** and select this repo (`render.yaml`). You still type the three secrets in the dashboard.

## 2. Vercel — web app

1. [vercel.com](https://vercel.com) → **Add New… → Project** → import `ahmedmsabha/academic-research-copilot`.
2. **Root Directory:** `apps/web`. Framework: Next.js.
3. Environment variable (Production and Preview):

```text
NEXT_PUBLIC_API_BASE_URL=https://<service>.onrender.com
```

That value is public (API origin, not a secret). It is inlined at build time — change it, then redeploy.

4. Deploy. Your site will be `https://<project>.vercel.app`.

## 3. Wire CORS

On the Render service → **Environment**, set:

```text
CORS_ORIGINS=https://<project>.vercel.app
```

Save (Render restarts the service). Then open `/workspace` and send a message.

## 4. Smoke test

1. Open `https://<project>.vercel.app/workspace` (wait if Render is waking up).
2. Upload a small synthetic PDF and wait until **Ready for search**.
3. Ask a document question, `What is 12 * (3 + 4)?`, and a weather or web-search question.
4. Confirm filename/page citations and **External tool** labels.

## Local Docker Compose (unchanged)

```bash
cp .env.example .env
# Set GEMINI_API_KEY
docker compose up --build
```

`DOCKER_BUILD=1` enables Next.js `output: "standalone"` only in the web Docker image — Vercel does not use standalone.

## After it is live

Put the Vercel URL in the README and LinkedIn draft.

Identity is still the development `X-User-Id` header (browser localStorage). Treat a public demo as shared-device scoped, not multi-tenant production auth.
