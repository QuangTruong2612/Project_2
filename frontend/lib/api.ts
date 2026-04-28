export interface ChatRequest {
  message: string;
  user_id: string;
  session_id?: string;
}

export interface ChatResponse {
  response: string;
  session_id: string;
  status: string;
}

/**
 * Gửi tin nhắn tới Next.js route handler /api/chat (server-side proxy
 * sang FastAPI backend). Dùng route handler để tránh CORS và để FE
 * không cần biết URL trực tiếp của backend.
 */
export async function sendChat(req: ChatRequest): Promise<ChatResponse> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Backend lỗi (${res.status}): ${text}`);
  }
  return (await res.json()) as ChatResponse;
}
