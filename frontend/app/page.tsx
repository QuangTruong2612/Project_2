"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { sendChat } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  ts: number;
}

const STORAGE_USER = "p2_user_id";
const STORAGE_SESSION = "p2_session_id";

function uuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

const SUGGESTIONS = [
  "Thời tiết Hà Nội hôm nay thế nào?",
  "Ghi chi tiêu: cà phê 35.000",
  "Tóm tắt tin tức mới nhất",
  "Tháng này tôi đã chi bao nhiêu?",
];

export default function Page() {
  const [userId, setUserId] = useState<string>("");
  const [sessionId, setSessionId] = useState<string>("");
  const [input, setInput] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Khôi phục user_id / session_id từ localStorage
  useEffect(() => {
    let uid = localStorage.getItem(STORAGE_USER);
    if (!uid) {
      uid = uuid();
      localStorage.setItem(STORAGE_USER, uid);
    }
    let sid = localStorage.getItem(STORAGE_SESSION);
    if (!sid) {
      sid = uuid();
      localStorage.setItem(STORAGE_SESSION, sid);
    }
    setUserId(uid);
    setSessionId(sid);
  }, []);

  // Auto scroll xuống tin nhắn mới
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, loading]);

  const handleNewSession = () => {
    const sid = uuid();
    localStorage.setItem(STORAGE_SESSION, sid);
    setSessionId(sid);
    setMessages([]);
    setError(null);
    inputRef.current?.focus();
  };

  const handleSend = async (textOverride?: string) => {
    const text = (textOverride ?? input).trim();
    if (!text || loading || !userId) return;

    const userMsg: Message = { role: "user", content: text, ts: Date.now() };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setError(null);
    setLoading(true);

    try {
      const res = await sendChat({
        message: text,
        user_id: userId,
        session_id: sessionId,
      });
      // Backend có thể tạo session_id mới nếu chưa có; lưu lại
      if (res.session_id && res.session_id !== sessionId) {
        setSessionId(res.session_id);
        localStorage.setItem(STORAGE_SESSION, res.session_id);
      }
      const botMsg: Message = {
        role: "assistant",
        content: res.response,
        ts: Date.now(),
      };
      setMessages((m) => [...m, botMsg]);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <main className="mx-auto flex h-screen max-w-3xl flex-col px-4 py-6">
      {/* Header */}
      <header className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-emerald-500 text-lg shadow">
            <span aria-hidden>🤖</span>
          </div>
          <div>
            <h1 className="text-lg font-semibold text-slate-800">
              Trợ lý cá nhân
            </h1>
            <p className="text-xs text-slate-500">
              Chi tiêu • Thời tiết • Tin tức
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={handleNewSession}
          className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 shadow-sm transition hover:border-indigo-300 hover:text-indigo-600"
        >
          Cuộc hội thoại mới
        </button>
      </header>

      {/* Chat area */}
      <section className="flex flex-1 flex-col overflow-hidden rounded-2xl border border-white/60 bg-white/70 shadow-xl shadow-indigo-100 backdrop-blur">
        <div
          ref={scrollRef}
          className="chat-scroll flex-1 overflow-y-auto px-4 py-6 sm:px-6"
        >
          {messages.length === 0 && (
            <EmptyState onPick={(s) => handleSend(s)} />
          )}

          <div className="space-y-4">
            {messages.map((m, i) => (
              <Bubble key={i} msg={m} />
            ))}
            {loading && <TypingBubble />}
          </div>
        </div>

        {error && (
          <div className="border-t border-rose-200 bg-rose-50 px-4 py-2 text-sm text-rose-700">
            {error}
          </div>
        )}

        {/* Input */}
        <div className="border-t border-slate-100 bg-white/80 p-3">
          <div className="flex items-end gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Nhập tin nhắn… (Enter để gửi, Shift+Enter để xuống dòng)"
              rows={1}
              className="max-h-40 flex-1 resize-none rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
            />
            <button
              type="button"
              onClick={() => handleSend()}
              disabled={loading || !input.trim()}
              className="inline-flex h-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-emerald-500 px-4 text-sm font-medium text-white shadow-md transition disabled:cursor-not-allowed disabled:opacity-50 hover:brightness-110"
            >
              Gửi
            </button>
          </div>
          <p className="mt-1.5 px-1 text-[11px] text-slate-400">
            user_id: <span className="font-mono">{userId.slice(0, 8)}…</span>{" "}
            • session: <span className="font-mono">{sessionId.slice(0, 8)}…</span>
          </p>
        </div>
      </section>
    </main>
  );
}

function EmptyState({ onPick }: { onPick: (s: string) => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
      <div className="text-4xl">👋</div>
      <div>
        <h2 className="text-lg font-medium text-slate-700">
          Mình giúp gì cho bạn hôm nay?
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Thử một trong các gợi ý bên dưới hoặc gõ câu hỏi của riêng bạn.
        </p>
      </div>
      <div className="grid w-full max-w-md grid-cols-1 gap-2 sm:grid-cols-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => onPick(s)}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-left text-sm text-slate-700 shadow-sm transition hover:border-indigo-300 hover:text-indigo-600"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

function Bubble({ msg }: { msg: Message }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm shadow-sm ${
          isUser
            ? "rounded-br-sm bg-gradient-to-br from-indigo-500 to-indigo-600 text-white"
            : "rounded-bl-sm bg-white text-slate-800 ring-1 ring-slate-100"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{msg.content}</p>
        ) : (
          <div className="prose-bubble">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {msg.content}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}

function TypingBubble() {
  return (
    <div className="flex justify-start">
      <div className="rounded-2xl rounded-bl-sm bg-white px-4 py-3 shadow-sm ring-1 ring-slate-100">
        <div className="flex items-center gap-1">
          <span className="h-2 w-2 animate-dot-1 rounded-full bg-slate-400" />
          <span className="h-2 w-2 animate-dot-2 rounded-full bg-slate-400" />
          <span className="h-2 w-2 animate-dot-3 rounded-full bg-slate-400" />
        </div>
      </div>
    </div>
  );
}
