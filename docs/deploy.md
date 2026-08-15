# Deploy

Production target: **two Dokploy applications** on your Hostinger VPS, plus **Prisma Postgres** (pgvector).

Do not add a second Postgres on the VPS. Keep the existing Prisma `DATABASE_URL`. Secrets stay server-side. Never put API keys or `DATABASE_URL` in `NEXT_PUBLIC_*` variables.

```text
Browser  →  Dokploy app “web” (Next.js, apps/web)
                │
                │  same-origin /api/v1  →  API_BASE_URL
                ▼
         Dokploy app “ai” (FastAPI, apps/ai-service)
                │
                └─ Prisma Postgres + pgvector
```

## 0. Prerequisites

- Dokploy on the VPS, GitHub repo connected
- Existing Prisma Postgres URL (`DATABASE_URL`) with the `vector` extension
- `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/apikey)

Apply migrations to the **same** database the AI service will use (from your laptop):

```bash
cd apps/web
npx prisma migrate deploy
```

## 1. Dokploy — AI service (backend)

Create an **Application** (not Compose) from this GitHub repo.

| Field | Value |
|---|---|
| Provider | GitHub, repo `academic-research-copilot`, branch `main` |
| Build type | **Dockerfile** (not Nixpacks) |
| Build path | `apps/ai-service` |
| Dockerfile | `Dockerfile` (relative to the build path — not `apps/ai-service/Dockerfile`) |
| Docker context | `apps/ai-service` or `.` if Dokploy already scopes context to the build path |
| Port | `8000` |

If the build fails with “Dockerfile not found”, the Dockerfile path is doubled. Use `Dockerfile` only, or set context to the repo root and Dockerfile to `apps/ai-service/Dockerfile` — not both.

### Environment variables

```text
APP_ENV=production
GEMINI_API_KEY=your-gemini-key
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/postgres?sslmode=require
CORS_ORIGINS=https://your-web-domain
STORAGE_PROVIDER=local
STORAGE_LOCAL_ROOT=/data/uploads
DEV_FAKE_LLM=false
DEV_FAKE_EMBEDDINGS=false
PORT=8000
```

You can set `CORS_ORIGINS` after the web app has a domain. No trailing slash.

### Volume (keep PDFs across redeploys)

Advanced → Mounts → volume:

- Volume name: `ai-uploads`
- Mount path: `/data/uploads`

If uploads fail with a permission error after the volume is attached, the mount is root-owned. Redeploy without the volume first to confirm the API works, then fix ownership on the volume.

### Domain

Domains → Generate domain (or attach your own). Set **port 8000**. Then:

```bash
curl https://<ai-domain>/health
# {"status":"ok","service":"ai-service"}

# /api is an index, not the app. Real routes are /api/v1/...
curl -i https://<ai-domain>/api/v1/projects
# 401 UNAUTHORIZED without X-User-Id — that means the API is reachable
```

## 2. Dokploy — web app

Second **Application**, same GitHub repo.

| Field | Value |
|---|---|
| Build type | **Dockerfile** |
| Build path | `apps/web` |
| Dockerfile | `Dockerfile` |
| Port | `3000` (the domain must also use port 3000) |

Environment variable (runtime — **not** a Next.js build argument):

```text
API_BASE_URL=https://<ai-domain>
```

Use the AI origin only. No `/api`, `/health`, `/api/v1`, or trailing slash.

```text
# Correct
API_BASE_URL=https://ai-xxxxx.dokploy.app

# Wrong — these are paths, not the base
API_BASE_URL=https://ai-xxxxx.dokploy.app/api
API_BASE_URL=https://ai-xxxxx.dokploy.app/health
API_BASE_URL=http://localhost:8000
```

`NEXT_PUBLIC_API_BASE_URL` is accepted as a fallback with the same value. After you change `API_BASE_URL`, **redeploy the web app** so the container picks up the env (a full rebuild is only required when the proxy code itself changes).

Generate a domain, port **3000**.

## 3. Wire CORS

The workspace UI calls the web app, which proxies to the AI service, so CORS is optional for `/workspace`. Still set it on the **AI** app if you open the API from the browser:

```text
CORS_ORIGINS=https://<web-domain>
```

No trailing slash. Redeploy the AI app. Then open `https://<web-domain>/workspace`.

## 4. Smoke test

1. Open `/workspace`.
2. Upload a PDF and wait until **Ready for search**.
3. Ask a document question, `What is 12 * (3 + 4)?`, and a weather or web-search question.
4. Confirm filename/page citations and **External tool** labels.

## Local Docker Compose (unchanged)

```bash
cp .env.example .env
# Set GEMINI_API_KEY
docker compose up --build
```

## After it is live

Put the **web** URL in the README and LinkedIn draft.

Identity is still the development `X-User-Id` header (browser localStorage). Treat a public demo as shared-device scoped, not multi-tenant production auth.
