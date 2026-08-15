# LinkedIn draft — Task 3: AI Agent with Tool Calling

I just shipped Task 3 of Academic Research Copilot: an agent that can choose a calculator, weather lookup, or web search before it answers.

**Problem**  
A research assistant should not guess arithmetic, invent the weather, or pretend uploaded PDFs are the live web. It needs to pick a tool, show what it used, and keep document citations honest.

**What I built**
- Constrained route selection (deterministic rules + JSON classification — not keyword-only)
- Safe calculator (restricted AST, never `eval`)
- Weather via Open-Meteo, labeled as an external tool
- Web search (DuckDuckGo Instant Answer, optional Tavily), with URL sources separate from PDF citations
- User-safe status only: “Using calculator”, “Checking weather”, “Searching the web”

**Technologies used:** Next.js, FastAPI, Google Gemini, Open-Meteo, DuckDuckGo/Tavily, Prisma Postgres + pgvector (RAG from Task 2 still in the same product).

**Challenges**
- Routing without stealing document questions (“weather in this paper” stays RAG)
- Keeping calculator exact when a project already has indexed PDFs
- Labeling external evidence so it cannot be mistaken for a page citation

**Lesson**  
Tool calling is a product contract: validate inputs, time out providers, and never let source text become instructions.

GitHub: https://github.com/ahmedmsabha/academic-research-copilot  
Try it: `/agent` after local setup  
Demo: record from docs/demo-script.md (add video link after publishing)

#AI #Agents #ToolCalling #FastAPI #NextJS #Gemini #BuildInPublic
