# LinkedIn post draft — Task 1

Copy, personalize, attach screenshots / demo clip, then publish.

---

Built my first AI chatbot for **Academic Research Copilot** 🎓

**Problem:** Students and researchers need a simple place to ask questions and keep conversation context without pasting API keys into the browser.

**What I shipped (Task 1):**
- Next.js chat UI with loading states and Markdown replies
- FastAPI backend calling **Google Gemini** (`google-genai`)
- Conversation history in **Prisma Postgres**
- Safe, user-facing errors (no stack traces)

**Stack:** Next.js · TypeScript · Tailwind · FastAPI · Pydantic · SQLAlchemy · Prisma Postgres · Gemini

**Challenges:**
- Keeping secrets server-side only (`GEMINI_API_KEY` never in `NEXT_PUBLIC_*`)
- Aligning Prisma schema/migrations with a Python AI service that owns runtime chat writes
- Designing problem-detail API errors that stay useful without leaking internals

**What I learned:**
- Clean separation: UI → typed API client → AI service → provider adapter
- Fake LLM providers make tests deterministic and free
- Durable storage early (Postgres) avoids rewriting chat persistence later

GitHub: https://github.com/ahmedmsabha/academic-research-copilot
Screenshots: see `docs/screenshots/`

#AI #FastAPI #NextJS #Gemini #BuildInPublic #StudentDeveloper

---

After publishing, paste the post URL here for your portfolio tracker.

## Show checklist

- [x] App runs locally (web :3000, AI :8000)
- [x] Screenshots in `docs/screenshots/`
- [x] Demo script in `docs/demo-script.md`
- [x] README updated
- [x] Initial git commit on `main`
- [x] Pushed to GitHub: https://github.com/ahmedmsabha/academic-research-copilot
- [ ] Record 2–3 min demo video
- [ ] Publish LinkedIn post (use draft above)
