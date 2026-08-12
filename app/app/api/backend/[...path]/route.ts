import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

function backendBaseUrl() {
  return (
    process.env.BACKEND_API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://127.0.0.1:8000"
  ).replace(/\/$/, "");
}

async function proxyBackend(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> | { path?: string[] } },
) {
  const params = await context.params;
  const path = params.path?.join("/") ?? "";
  const url = new URL(request.url);
  const backendUrl = `${backendBaseUrl()}/${path}${url.search}`;

  const requestHeaders = new Headers(request.headers);
  requestHeaders.delete("host");
  requestHeaders.delete("connection");

  let response: Response;
  try {
    response = await fetch(backendUrl, {
      method: request.method,
      headers: requestHeaders,
      body:
        request.method === "GET" || request.method === "HEAD"
          ? undefined
          : request.body,
      cache: "no-store",
      duplex: "half",
    } as RequestInit & { duplex: "half" });
  } catch {
    return Response.json(
      {
        error:
          "Could not reach the backend. Make sure FastAPI is running on http://localhost:8000.",
      },
      { status: 502 },
    );
  }

  const responseHeaders = new Headers(response.headers);
  for (const header of HOP_BY_HOP_HEADERS) {
    responseHeaders.delete(header);
  }

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders,
  });
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> | { path?: string[] } },
) {
  return proxyBackend(request, context);
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> | { path?: string[] } },
) {
  return proxyBackend(request, context);
}
