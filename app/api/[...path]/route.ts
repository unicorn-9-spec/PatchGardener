import { NextRequest } from "next/server";
export const dynamic = "force-dynamic";
export const runtime = "nodejs";

async function proxy(request: NextRequest, context: {params: Promise<{path: string[]}>}) {
  const {path} = await context.params;
  const route = path.join("/");
  if (!/^(health|repositories|scans|proposals(?:\/[a-f0-9]{32})?|approvals|exports\/[a-f0-9]{32}|audit)$/.test(route)) {
    return new Response("Unknown API route", {status: 404});
  }
  const origin = request.headers.get("origin");
  const host = request.headers.get("host");
  if (!["127.0.0.1:3105", "localhost:3105", "[::1]:3105"].includes(host || "")) return new Response("Unknown local host", {status: 403});
  // Next's canonical nextUrl origin can be localhost even when the browser
  // loaded 127.0.0.1. Compare against the validated incoming Host instead.
  if (request.method === "POST" && origin && origin !== `http://${host}`) return new Response("Cross-origin request rejected", {status: 403});
  const backend = new URL(process.env.PG_API_URL || "http://127.0.0.1:8105");
  if (!["127.0.0.1", "localhost", "[::1]"].includes(backend.hostname) || backend.protocol !== "http:") return new Response("Backend must be loopback HTTP", {status: 500});
  try {
    const body = request.method === "POST" ? await request.text() : undefined;
    if (body && body.length > 16000) return new Response("Request too large", {status: 413});
    const response = await fetch(`${backend.origin}/api/${route}`, {method: request.method, headers: {"Content-Type": "application/json"}, body, cache: "no-store", signal: AbortSignal.timeout(210000)});
    const headers = new Headers({"Content-Type": response.headers.get("Content-Type") || "application/json", "Cache-Control": "no-store"});
    const disposition = response.headers.get("Content-Disposition");
    if (disposition) headers.set("Content-Disposition", disposition);
    return new Response(response.body, {status: response.status, headers});
  } catch {
    return new Response("Backend unavailable. Start FastAPI on 127.0.0.1:8105; see README.md.", {status: 503});
  }
}
export { proxy as GET, proxy as POST };
