"use client";

import { FormEvent, KeyboardEvent, useState } from "react";

type ChatComposerProps = {
  disabled: boolean;
  onSend: (content: string) => Promise<void> | void;
  examplePrompts?: string[];
};

export function ChatComposer({ disabled, onSend, examplePrompts }: ChatComposerProps) {
  const [value, setValue] = useState("");
  const trimmed = value.trim();
  const canSend = !disabled && trimmed.length > 0;

  async function submit() {
    if (!canSend) {
      return;
    }
    const content = trimmed;
    setValue("");
    await onSend(content);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submit();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submit();
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="border-t border-line bg-white/80 px-4 py-4 backdrop-blur sm:px-6"
    >
      <label htmlFor="chat-input" className="sr-only">
        Message
      </label>
      <div className="mx-auto flex max-w-3xl flex-col gap-3">
        {examplePrompts && examplePrompts.length > 0 ? (
          <div className="flex flex-wrap gap-2" aria-label="Example prompts">
            {examplePrompts.map((prompt) => (
              <button
                key={prompt}
                type="button"
                disabled={disabled}
                onClick={() => {
                  void onSend(prompt);
                }}
                className="rounded-full border border-line bg-paper px-3 py-1.5 text-left text-xs text-ink transition hover:border-accent/50 hover:bg-accent-soft disabled:cursor-not-allowed disabled:opacity-40"
              >
                {prompt}
              </button>
            ))}
          </div>
        ) : null}
        <div className="flex items-end gap-3">
          <textarea
            id="chat-input"
            name="message"
            rows={2}
            value={value}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder="Ask anything… (Enter to send, Shift+Enter for a new line)"
            className="min-h-[3.25rem] flex-1 resize-y rounded-xl border border-line bg-paper px-3 py-2 text-ink outline-none ring-accent focus:ring-2 disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={!canSend}
            className="rounded-xl bg-accent px-4 py-2.5 font-medium text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </div>
    </form>
  );
}
