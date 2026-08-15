import Link from "next/link";

const navItems = [
  { href: "/", label: "Overview" },
  { href: "/workspace", label: "Workspace" },
  { href: "/chat", label: "Chat" },
  { href: "/rag", label: "Documents & RAG" },
  { href: "/agent", label: "Agent tools" },
  { href: "/prompt-lab", label: "Prompt Lab" },
] as const;

export function AppNav({ currentPath }: { currentPath: string }) {
  return (
    <header className="border-b border-line/80 bg-white/55 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div>
          <p className="font-display text-lg text-ink">Academic Research Copilot</p>
          <p className="text-sm text-ink-muted">Complete AI assistant for research</p>
        </div>
        <nav aria-label="Primary" className="flex flex-wrap gap-2">
          {navItems.map((item) => {
            const active = currentPath === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`rounded-xl px-3 py-2 text-sm transition ${
                  active
                    ? "bg-accent text-white"
                    : "border border-line bg-white/70 text-ink hover:bg-accent-soft"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
