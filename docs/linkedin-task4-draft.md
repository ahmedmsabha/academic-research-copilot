# LinkedIn draft — Task 4: Prompt Engineering Playground

I just shipped Task 4 of Academic Research Copilot: a Prompt Lab that compares prompting techniques on the same research question.

**Problem**  
Prompting advice is usually anecdotal. Students need to *see* how zero-shot, one-shot, few-shot, step-by-step, and structured output differ — without leaking hidden model reasoning.

**What I built**
- Versioned prompt templates (`prompt-lab-v1`) as application assets, not copy-pasted strings
- Side-by-side comparison for one input across five strategies
- Visible step-by-step (pedagogical CoT) vs structured JSON that is parsed before display
- Timing and token usage when the provider returns them; cost stays unavailable rather than guessed
- Manual ratings: accuracy, clarity, research usefulness
- Project-scoped experiment history

**Technologies used:** Next.js, FastAPI, Google Gemini, Prisma Postgres, versioned prompt templates.

**Challenges**
- Task 4 asks for chain-of-thought; the product rules forbid exposing hidden scratchpad. I implemented CoT as numbered *student-facing* working, and kept `structured` as parsed fields only.
- Keeping comparisons fair: same model settings, independent runs, no undocumented cost formula.

**Lesson**  
Prompt engineering is a product surface: templates need versions, validation, and an honest empty/error/success UI — not just a clever system prompt.

GitHub: https://github.com/ahmedmsabha/academic-research-copilot  
Try it: `/prompt-lab` after local setup  
Write-up: docs/prompt-comparison-report.md  
Demo: record from docs/demo-script.md (add video link after publishing)

#PromptEngineering #LLM #FastAPI #NextJS #Gemini #BuildInPublic
