import { NextRequest, NextResponse } from "next/server";

import { readUpstreamApiBaseUrl } from "@/lib/api-base-url";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

const SKIP_HEADERS = new Set([
  "accept-encoding",
  "connection",
  "content-length",
  "host",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
]);

type RouteContext = { params: Promise<{ path: string[] }> };

function problem(status: number, code: string, message: string): NextResponse {
  return NextResponse.json({ error: { code, message } }, { status });
}

async function proxy(request: NextRequest, context: RouteContext): Promise<NextResponse> {
  let upstream: string;
  try {
    const resolved = readUpstreamApiBaseUrl();
    if (!resolved) {
      return problem(
        500,
        "CONFIG_ERROR",
        "API_BASE_URL is not configured on the web app.",
      );
    }
    upstream = resolved;
  } catch (error) {
    const message = error instanceof Error ? error.message : "API_BASE_URL is invalid.";
    return problem(500, "CONFIG_ERROR", message);
  }

  const upstreamUrl = new URL(upstream);
  if (upstreamUrl.host === request.nextUrl.host) {
    return problem(
      500,
      "CONFIG_ERROR",
      "API_BASE_URL must be the AI service origin, not the web app URL.",
    );
  }

  const { path } = await context.params;
  const target = `${upstream}/api/v1/${path.join("/")}${request.nextUrl.search}`;
  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!SKIP_HEADERS.has(key.toLowerCase())) {
      headers.set(key, value);
    }
  });

  const method = request.method.toUpperCase();
  const hasBody = method !== "GET" && method !== "HEAD";

  let response: Response;
  try {
    response = await fetch(target, {
      method,
      headers,
      body: hasBody ? await request.arrayBuffer() : undefined,
      redirect: "manual",
      cache: "no-store",
    });
  } catch {
    return problem(
      502,
      "NETWORK_ERROR",
      "Unable to reach the AI service. Is it running on the configured API URL?",
    );
  }

  const outHeaders = new Headers();
  response.headers.forEach((value, key) => {
    if (!SKIP_HEADERS.has(key.toLowerCase())) {
      outHeaders.set(key, value);
    }
  });

  return new NextResponse(response.body, {
    status: response.status,
    headers: outHeaders,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
