# Deploy

Production target: **Vercel** for `apps/web`, **Railway** for `apps/ai-service`, **Prisma Postgres** (pgvector) for the database.

This repo is a monorepo. Railway does not need a separate GitHub repo. You import the same repo and set the service **Root Directory** to `apps/ai-service`.

Secrets stay server-side. Never put API keys or `DATABASE_URL` in `NEXT_PUBLIC_*` variables.

```text
Browser  →  Vercel (Next.js)  →  Railway (FastAPI)
                                      │
                                      └─ Prisma Postgres + pgvector
```

## 0. Prerequisites

- [Vercel](https://vercel.com) account connected to GitHub
- [Railway](https://railway.com) account connected to GitHub
- Existing Prisma Postgres URL (`DATABASE_URL`) with the `vector` extension
- `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/apikey)

Apply migrations to the **same** database the AI service will use:

```bash
cd apps/web
npx prisma migrate deploy
```

## 1. Railway — AI service (monorepo)

Railway treats each **service** as one app. The GitHub repo stays one repo.

1. Open [railway.com/new](https://railway.com/new) → **Deploy from GitHub repo**.
2. Select `academic-research-copilot`.
3. If Railway tries to deploy the whole repo or the Next.js app, that is fine — you will isolate the backend next. Prefer **Add a service → GitHub repo** so you have one service for the API only.
4. Open that service → **Settings**:

   | Setting | Value |
   |---|---|
   | Root Directory | `/apps/ai-service` |
   | Config File Path | `/apps/ai-service/railway.toml` |
   | Watch Paths | `/apps/ai-service/**` |

   Root Directory tells Railway to build only `apps/ai-service` (Dockerfile, `app/`, `pyproject.toml`). Web and docs changes will not rebuild the API if Watch Paths are set.

   The config file path is **absolute from the repo root**. Railway does not look inside Root Directory for `railway.toml`.

5. **Variables** (service → Variables). Do not create a Railway Postgres for this app — keep Prisma Postgres (pgvector):

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

Railway injects `PORT`. The Dockerfile already listens on `$PORT`. Do not put `GEMINI_API_KEY` or `DATABASE_URL` on Vercel.

You can set `CORS_ORIGINS` to a placeholder and fix it after Vercel is live. No trailing slash.

6. Deploy. Generate a public domain: service → **Settings → Networking → Generate domain**.

7. Check:

```bash
curl https://<your-service>.up.railway.app/health
# {"status":"ok","service":"ai-service"}
```

If the deploy fails, open the service **Deployments → Logs**. A missing `GEMINI_API_KEY` or `DATABASE_URL` stops production startup.

`apps/ai-service/railway.toml` sets the Docker builder and `/health` check. After you push it, Railway reads it from `/apps/ai-service/railway.toml`.

## 2. Vercel — web app

1. [vercel.com](https://vercel.com) → **Add New… → Project** → import the **same** GitHub repo.
2. **Root Directory:** `apps/web`. Framework: Next.js.
3. Environment variable (Production and Preview):

```text
NEXT_PUBLIC_API_BASE_URL=https://<your-service>.up.railway.app
```

That value is public (API origin, not a secret). It is inlined at build time — change it, then redeploy.

4. Deploy. Your site will be `https://<project>.vercel.app`.

## 3. Wire CORS

On Railway → Variables, set:

```text
CORS_ORIGINS=https://<project>.vercel.app
```

Railway restarts the service. Then open `/workspace` and send a message.

## 4. Smoke test

1. Open `https://<project>.vercel.app/workspace`.
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
