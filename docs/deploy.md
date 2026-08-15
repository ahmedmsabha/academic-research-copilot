# Deploy

Academic Research Copilot is two services plus PostgreSQL with pgvector. Secrets stay server-side. Never put API keys in `NEXT_PUBLIC_*` variables.

## Option A — Docker Compose (recommended local / VPS)

1. Copy `.env.example` to `.env` and set `GEMINI_API_KEY`.
2. From the repository root:

```bash
docker compose up --build
```

3. Open [http://localhost:3000](http://localhost:3000). The browser calls the AI service at `http://localhost:8000`.
4. Compose starts PostgreSQL + pgvector, runs Prisma migrations, then the FastAPI and Next.js services.

Named volumes persist the database and uploaded PDFs. Do not bake secrets into images.

To stop:

```bash
docker compose down
```

## Option B — Split hosts (Vercel + container + Prisma Postgres)

This matches a typical portfolio deploy.

| Piece | Suggested host |
|---|---|
| `apps/web` | Vercel or any Node host |
| `apps/ai-service` | Render, Railway, Fly.io, or a VPS running the AI-service Docker image |
| Database | Prisma Postgres or managed PostgreSQL with the `vector` extension |
| PDF files | Persistent volume on the AI service (`STORAGE_LOCAL_ROOT`) |

### Web

Set:

```text
NEXT_PUBLIC_API_BASE_URL=https://your-ai-service.example
```

This value is public (it is the API origin, not a secret). Rebuild the web app after changing it.

### AI service

Set at least:

```text
APP_ENV=production
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DB?sslmode=require
GEMINI_API_KEY=...
CORS_ORIGINS=https://your-web.example
STORAGE_LOCAL_ROOT=/data/uploads
```

`APP_ENV=production` rejects `DEV_FAKE_LLM` / `DEV_FAKE_EMBEDDINGS` and requires `GEMINI_API_KEY` and `DATABASE_URL`.

Apply Prisma migrations against the same database before traffic:

```bash
cd apps/web
npx prisma migrate deploy
```

### Health

`GET https://your-ai-service.example/health` → `{ "status": "ok", "service": "ai-service" }`

## After deploy

1. Open `/workspace`.
2. Upload a small synthetic PDF and wait until **Ready for search**.
3. Ask a document question, a calculator question, and a weather question.
4. Confirm citations and external-tool labels.
5. Add the live URL to the README and LinkedIn post.

Identity is still the development `X-User-Id` header (browser localStorage). Treat a public demo as shared-device scoped, not multi-tenant production auth.
