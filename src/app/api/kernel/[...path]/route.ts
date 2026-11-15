import { NextRequest, NextResponse } from "next/server";
export const runtime = "nodejs";
async function forward(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  if (path[0] !== "v1" || path.some(part => !/^[a-zA-Z0-9_.-]+$/.test(part))) return NextResponse.json({ error: { message: "Invalid kernel route" } }, { status: 400 });
  if (request.headers.get("origin") && request.headers.get("origin") !== request.nextUrl.origin) return NextResponse.json({ error: { message: "Cross-origin writes are unavailable" } }, { status: 403 });
  try {
    const url = new URL(process.env.KERNEL_API_URL || "http://127.0.0.1:8000");
    if (!["127.0.0.1", "localhost"].includes(url.hostname)) throw new Error("Kernel must use a loopback address");
    url.pathname = "/" + path.join("/"); url.search = request.nextUrl.search;
    const body = ["GET", "HEAD"].includes(request.method) ? undefined : await request.text();
    if (body && body.length > 5_000_000) return NextResponse.json({ error: { message: "Request too large; split the import" } }, { status: 413 });
    if (body) JSON.parse(body);
    const response = await fetch(url, { method: request.method, body, headers: { "Content-Type": "application/json" }, signal: AbortSignal.timeout(path.includes("intelligence") ? 95_000 : 25_000), cache: "no-store" });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch { return NextResponse.json({ error: { message: "Kernel unavailable or request invalid. Start the local Python service and retry. Your browser backup is preserved." } }, { status: 503 }); }
}
export { forward as GET, forward as POST, forward as PATCH, forward as PUT, forward as DELETE };
