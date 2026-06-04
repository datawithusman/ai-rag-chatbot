"use client";

import { useState, useRef, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import {
  Upload,
  Send,
  FileText,
  Loader2,
  Trash2,
  Bot,
  User,
  X,
} from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: { document_name: string; page_number: number | null; relevance_score: number }[];
}

interface Document {
  document_id: string;
  filename: string;
  status: string;
  chunk_count: number;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_URL}/api/v1/documents/upload`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("Upload failed");
      const data = await res.json();
      setDocuments((prev) => [
        ...prev,
        {
          document_id: data.document_id,
          filename: data.filename,
          status: data.status,
          chunk_count: data.chunk_count,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Failed to upload document. Please try again." },
      ]);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
      scrollToBottom();
    }
  };

  const handleDelete = async (docId: string) => {
    try {
      await fetch(`${API_URL}/api/v1/documents/${docId}`, { method: "DELETE" });
      setDocuments((prev) => prev.filter((d) => d.document_id !== docId));
    } catch { /* ignore */ }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const question = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setIsLoading(true);
    scrollToBottom();

    try {
      const res = await fetch(`${API_URL}/api/v1/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Chat request failed");
      }
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          sources: data.sources,
        },
      ]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Something went wrong";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${msg}` },
      ]);
    } finally {
      setIsLoading(false);
      scrollToBottom();
    }
  };

  return (
    <div className="flex h-screen">
      {/* ── Sidebar ─────────────────────────────────────── */}
      <aside className="w-80 border-r border-gray-200 bg-white flex flex-col">
        <div className="p-4 border-b border-gray-100">
          <h1 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <Bot className="w-6 h-6 text-primary-600" />
            AI RAG Chatbot
          </h1>
          <p className="text-xs text-gray-500 mt-1">
            Upload PDFs & ask questions
          </p>
        </div>

        <div className="p-4">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleUpload}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 font-medium text-sm"
          >
            {isUploading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Upload className="w-4 h-4" />
            )}
            {isUploading ? "Processing..." : "Upload PDF"}
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4">
          <h2 className="text-xs font-semibold text-gray-400 uppercase mb-2">
            Documents ({documents.length})
          </h2>
          {documents.length === 0 ? (
            <p className="text-sm text-gray-400 italic">
              No documents uploaded yet
            </p>
          ) : (
            <div className="space-y-2">
              {documents.map((doc) => (
                <div
                  key={doc.document_id}
                  className="flex items-center justify-between p-2.5 bg-gray-50 rounded-lg group"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <FileText className="w-4 h-4 text-primary-500 shrink-0" />
                    <span className="text-sm text-gray-700 truncate">
                      {doc.filename}
                    </span>
                  </div>
                  <button
                    onClick={() => handleDelete(doc.document_id)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <X className="w-3.5 h-3.5 text-gray-400 hover:text-red-500" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="p-4 border-t border-gray-100 text-center">
          <p className="text-xs text-gray-400">
            Built by{" "}
            <a
              href="https://datawithusman.com"
              target="_blank"
              className="text-primary-500 hover:underline"
            >
              Usman
            </a>
          </p>
        </div>
      </aside>

      {/* ── Chat Area ───────────────────────────────────── */}
      <main className="flex-1 flex flex-col">
        <header className="px-6 py-3 border-b border-gray-200 bg-white">
          <h2 className="font-semibold text-gray-800">Chat with your Documents</h2>
          <p className="text-xs text-gray-500">
            Ask anything about your uploaded PDFs
          </p>
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
              <Bot className="w-16 h-16 mb-4 text-primary-200" />
              <p className="text-lg font-medium">No messages yet</p>
              <p className="text-sm mt-1">
                Upload a PDF and start asking questions!
              </p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.role === "assistant" && (
                <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4 text-primary-600" />
                </div>
              )}
              <div className="max-w-2xl">
                <div
                  className={msg.role === "user" ? "chat-bubble-user" : "chat-bubble-ai"}
                >
                  {msg.role === "assistant" ? (
                    <div className="prose prose-sm max-w-none">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  ) : (
                    msg.content
                  )}
                </div>
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {msg.sources.map((s, j) => (
                      <span
                        key={j}
                        className="inline-flex items-center gap-1 text-xs bg-primary-50 text-primary-700 px-2 py-1 rounded-full"
                      >
                        <FileText className="w-3 h-3" />
                        {s.document_name}
                        {s.page_number && ` (p.${s.page_number})`}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              {msg.role === "user" && (
                <div className="w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center shrink-0">
                  <User className="w-4 h-4 text-white" />
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="flex gap-3 items-start">
              <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-primary-600" />
              </div>
              <div className="chat-bubble-ai flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-primary-500" />
                <span className="text-sm text-gray-500">Thinking...</span>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <form
          onSubmit={handleSubmit}
          className="px-6 py-4 border-t border-gray-200 bg-white"
        >
          <div className="flex gap-3 max-w-4xl mx-auto">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question about your documents..."
              className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="px-4 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}