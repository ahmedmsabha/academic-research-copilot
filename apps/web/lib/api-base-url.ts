/**
 * Resolve the AI service origin. Dokploy/runtime env is read dynamically so
 * Next.js does not bake the value into the server bundle at build time.
 */
export function readUpstreamApiBaseUrl(): string | undefined {
  const raw = process.env["API_BASE_URL"] ?? process.env["NEXT_PUBLIC_API_BASE_URL"];
  if (!raw?.trim()) {
    return undefined;
  }
  return normalizeApiBaseUrl(raw);
}

export function normalizeApiBaseUrl(raw: string): string {
  const trimmed = raw.trim();
  let parsed: URL;
  try {
    parsed = new URL(trimmed);
  } catch {
    throw new Error("API base URL must be an absolute URL, for example https://ai.example.com");
  }

  let path = parsed.pathname.replace(/\/+$/, "");
  const accidentalSuffixes = ["/api/health", "/api/v1", "/health", "/api"];
  for (const suffix of accidentalSuffixes) {
    if (path === suffix || path.endsWith(suffix)) {
      path = path.slice(0, -suffix.length);
      break;
    }
  }
  path = path.replace(/\/+$/, "");
  return `${parsed.origin}${path}`;
}
