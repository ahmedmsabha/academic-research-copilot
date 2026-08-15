# Deploy

Production target: **Vercel** for `apps/web`, **Fly.io** for `apps/ai-service`, **Prisma Postgres** (pgvector) for the database.

Secrets stay server-side. Never put API keys or `DATABASE_URL` in `NEXT_PUBLIC_*` variables.

```text
Browser  →  Vercel (Next.js)  →  Fly.io (FastAPI)
                                      │
                                      ├─ Prisma Postgres + pgvector
                                      └─ Fly volume  /data/uploads  (PDFs)
```

## 0. Prerequisites

- [Vercel](https://vercel.com) account connected to GitHub
- [Fly.io](https://fly.io) account and the [flyctl](https://fly.io/docs/flyctl/install/) CLI
- Existing Prisma Postgres URL (`DATABASE_URL`) with the `vector` extension
- `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/apikey)

Install flyctl and log in:

```bash
fly auth login
```

Apply migrations to the **same** database the AI service will use:

```bash
cd apps/web
npx prisma migrate deploy
```

## 1. Fly.io — AI service

From `apps/ai-service` (this folder already has `Dockerfile` and `fly.toml`):

```bash
cd apps/ai-service
fly launch --no-deploy --copy-config --name academic-research-copilot-ai --region fra
```

If the app name is taken, pick another. Note the hostname: `https://<app-name>.fly.dev`.

Set secrets (replace values; do not commit them):

```bash
fly secrets set \
  GEMINI_API_KEY="your-gemini-key" \
  DATABASE_URL="postgresql://USER:PASSWORD@HOST:5432/postgres?sslmode=require" \
  CORS_ORIGINS="https://your-app.vercel.app"
```

Optional: `WEB_SEARCH_API_KEY` for Tavily.

`fly.toml` creates a 1 GB volume at `/data/uploads` on first deploy (`initial_size`). Deploy:

```bash
fly deploy
```

Check:

```bash
curl https://<app-name>.fly.dev/health
# {"status":"ok","service":"ai-service"}
```

If the health check fails, `fly logs` and `fly status` show startup errors (missing secret, DB, or port).

## 2. Vercel — web app

1. In the Vercel dashboard: **Add New… → Project** and import `ahmedmsabha/academic-research-copilot`.
2. Set **Root Directory** to `apps/web` (Vercel monorepo setting). Framework: Next.js.
3. Environment variable (Production and Preview):

```text
NEXT_PUBLIC_API_BASE_URL=https://<app-name>.fly.dev
```

That value is public (API origin, not a secret). It is inlined at build time — change it, then redeploy.

4. Deploy. Your site will be `https://<project>.vercel.app`.

## 3. Wire CORS

After you know the Vercel URL, update Fly:

```bash
cd apps/ai-service
fly secrets set CORS_ORIGINS="https://<project>.vercel.app"
```

No trailing slash. Add more origins as a comma-separated list if you also use a custom domain.

Then confirm `/workspace` can list projects and send a message.

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

Compose still uses local Postgres + pgvector. `DOCKER_BUILD=1` enables Next.js `output: "standalone"` only in the web Docker image — Vercel does not use standalone.

## After it is live

Put the Vercel URL in the README and LinkedIn draft.

Identity is still the development `X-User-Id` header (browser localStorage). Treat a public demo as shared-device scoped, not multi-tenant production auth.
