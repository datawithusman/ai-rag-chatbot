import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI RAG Chatbot — Ask Your Documents",
  description:
    "Upload PDFs and get AI-powered answers. Built with FastAPI, LangChain, ChromaDB & Next.js.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50">{children}</body>
    </html>
  );
}