"use client";

import { useEffect, useRef, useState } from "react";

import { ApiError, api } from "@/lib/api";
import type { Document, DocumentStatus } from "@/types/api";

const PROCESSING_STATUSES: DocumentStatus[] = [
  "uploaded",
  "queued",
  "extracting",
  "chunking",
  "embedding",
  "indexing",
];

type DocumentPanelProps = {
  projectId: string | null;
};

function formatBytes(size: number): string {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function formatUploadDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return "Unknown date";
  }
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function statusLabel(status: DocumentStatus): string {
  switch (status) {
    case "ready":
      return "Ready for search";
    case "failed":
      return "Indexing failed";
    case "queued":
      return "Queued";
    case "extracting":
      return "Extracting text";
    case "chunking":
      return "Chunking";
    case "embedding":
      return "Embedding";
    case "indexing":
      return "Indexing";
    default:
      return "Uploaded";
  }
}

export function DocumentPanel({ projectId }: DocumentPanelProps) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!projectId) {
      setDocuments([]);
      return;
    }

    const activeProjectId = projectId;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const items = await api.listDocuments(activeProjectId);
        if (!cancelled) {
          setDocuments(items);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Unable to load documents.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const processingKey = documents
    .filter((doc) => PROCESSING_STATUSES.includes(doc.status))
    .map((doc) => doc.id)
    .join(",");

  useEffect(() => {
    if (!projectId || !processingKey) {
      return;
    }

    const timer = window.setInterval(() => {
      void api
        .listDocuments(projectId)
        .then((items) => setDocuments(items))
        .catch(() => {
          // Keep the last known list; transient poll errors are non-fatal.
        });
    }, 2000);

    return () => window.clearInterval(timer);
  }, [projectId, processingKey]);

  async function handleUpload(fileList: FileList | null) {
    if (!projectId || !fileList || fileList.length === 0) {
      return;
    }
    const file = fileList[0];
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are supported.");
      return;
    }

    setUploading(true);
    setError(null);
    try {
      const created = await api.uploadDocument(projectId, file);
      setDocuments((prev) => [created, ...prev.filter((doc) => doc.id !== created.id)]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed. Please try again.");
    } finally {
      setUploading(false);
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    }
  }

  async function handleRetry(documentId: string) {
    if (!projectId) {
      return;
    }
    const current = documents.find((doc) => doc.id === documentId);
    if (
      current &&
      PROCESSING_STATUSES.includes(current.status) &&
      !window.confirm(
        "This file is still marked as indexing. Retry anyway? Use this if Embedding looks stuck after a server deploy.",
      )
    ) {
      return;
    }
    setBusyId(documentId);
    setError(null);
    try {
      const updated = await api.retryDocument(projectId, documentId);
      setDocuments((prev) => prev.map((doc) => (doc.id === documentId ? updated : doc)));
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Retry failed. Please try again.",
      );
      try {
        const items = await api.listDocuments(projectId);
        setDocuments(items);
      } catch {
        // Keep the last known list if refresh fails.
      }
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(document: Document) {
    if (!projectId) {
      return;
    }
    const confirmed = window.confirm(
      `Delete “${document.filename}”? This removes it from search and cannot be undone.`,
    );
    if (!confirmed) {
      return;
    }
    setBusyId(document.id);
    setError(null);
    try {
      await api.deleteDocument(projectId, document.id);
      setDocuments((prev) => prev.filter((doc) => doc.id !== document.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Delete failed. Please try again.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section
      className="flex h-full min-h-[320px] flex-col overflow-hidden rounded-3xl border border-line bg-white/70 shadow-[0_20px_60px_rgba(28,36,48,0.08)] backdrop-blur"
      aria-labelledby="documents-heading"
    >
      <header className="border-b border-line px-5 py-4">
        <p className="text-xs uppercase tracking-[0.18em] text-ink-muted">Task 2 · RAG</p>
        <h2 id="documents-heading" className="font-display text-xl text-ink">
          Project documents
        </h2>
        <p className="mt-1 text-sm text-ink-muted">
          Chat can search a file only after it is Ready for search. Uploading is not enough.
        </p>
      </header>

      <div className="border-b border-line px-5 py-4">
        <label className="block text-sm font-medium text-ink" htmlFor="pdf-upload">
          Upload PDF
        </label>
        <input
          id="pdf-upload"
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          disabled={!projectId || uploading}
          className="mt-2 block w-full text-sm text-ink-muted file:mr-3 file:rounded-lg file:border-0 file:bg-accent file:px-3 file:py-2 file:text-sm file:font-medium file:text-white disabled:opacity-60"
          onChange={(event) => void handleUpload(event.target.files)}
        />
        <p className="mt-2 text-xs text-ink-muted" aria-live="polite">
          {uploading
            ? "Uploading and queuing for indexing…"
            : "PDF only. Prefer a short text paper or one chapter (under ~40 pages). Scans use on-server OCR and take longer."}
        </p>
      </div>

      {error ? (
        <div
          role="alert"
          className="mx-5 mt-4 rounded-xl border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger"
        >
          {error}
        </div>
      ) : null}

      <div className="flex-1 overflow-y-auto px-5 py-4">
        {!projectId || loading ? (
          <p className="text-sm text-ink-muted" aria-busy="true">
            {projectId ? "Loading documents…" : "Preparing workspace…"}
          </p>
        ) : documents.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-line px-4 py-8 text-center">
            <p className="font-display text-lg text-ink">No documents yet</p>
            <p className="mt-2 text-sm text-ink-muted">
              Upload a PDF to enable grounded answers with source pages.
            </p>
          </div>
        ) : (
          <ul className="space-y-3">
            {documents.map((document) => {
              const processing = PROCESSING_STATUSES.includes(document.status);
              const busy = busyId === document.id;
              return (
                <li
                  key={document.id}
                  className="rounded-2xl border border-line bg-paper/60 px-4 py-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate font-medium text-ink">{document.filename}</p>
                      <p className="mt-1 text-xs text-ink-muted">
                        Uploaded {formatUploadDate(document.created_at)}
                        {" · "}
                        {formatBytes(document.size_bytes)}
                        {document.page_count != null ? ` · ${document.page_count} pages` : ""}
                        {" · "}
                        <span
                          className={
                            document.status === "ready"
                              ? "text-accent"
                              : document.status === "failed"
                                ? "text-danger"
                                : ""
                          }
                        >
                          {statusLabel(document.status)}
                          {processing ? "…" : ""}
                        </span>
                      </p>
                      {document.status === "failed" && document.failure_message ? (
                        <p className="mt-2 text-xs text-danger">{document.failure_message}</p>
                      ) : null}
                      {processing ? (
                        <p className="mt-2 text-xs text-ink-muted">
                          Not searchable yet. If this stays on Embedding after a deploy,
                          use Retry indexing.
                        </p>
                      ) : null}
                      {document.page_count != null && document.page_count >= 80 ? (
                        <p className="mt-2 text-xs text-ink-muted">
                          This PDF is very long ({document.page_count} pages). A chapter or
                          paper under ~40 pages indexes more reliably on the server.
                        </p>
                      ) : null}
                      {document.status !== "ready" && document.status !== "failed" ? (
                        <p className="sr-only" aria-live="polite">
                          {document.filename} is {statusLabel(document.status)}
                        </p>
                      ) : null}
                    </div>
                    <div className="flex shrink-0 flex-col gap-2">
                      {document.status === "failed" || processing ? (
                        <button
                          type="button"
                          className="rounded-lg border border-line px-2 py-1 text-xs text-ink disabled:opacity-50"
                          disabled={busy}
                          onClick={() => void handleRetry(document.id)}
                        >
                          Retry indexing
                        </button>
                      ) : null}
                      <button
                        type="button"
                        className="rounded-lg border border-danger/30 px-2 py-1 text-xs text-danger disabled:opacity-50"
                        disabled={busy}
                        onClick={() => void handleDelete(document)}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
}
