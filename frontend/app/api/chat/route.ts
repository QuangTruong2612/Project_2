import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

/**
 * Proxy server-side sang FastAPI backend.
 * BACKEND_URL được inject qua biến môi trường (xem docker-compose.yml).
 */
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  let payload: unknown;
  try {
    payload = await req.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON" }, { status: 400 });
  }

  const upstream = await fetch(`${BACKEND_URL}/api/v1/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  }).catch((err) => {
    return new Response(
      JSON.stringify({ detail: `Không kết nối được backend: ${err.message}` }),
      { status: 502, headers: { "Content-Type": "application/json" } },
    );
  });

  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: {
      "Content-Type":
        upstream.headers.get("Content-Type") ?? "application/json",
    },
  });
}
