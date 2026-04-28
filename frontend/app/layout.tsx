import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Trợ lý cá nhân AI",
  description: "Chatbot hỗ trợ chi tiêu, thời tiết, tin tức",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body className="bg-gradient-to-br from-indigo-50 via-white to-emerald-50 min-h-screen">
        {children}
      </body>
    </html>
  );
}
