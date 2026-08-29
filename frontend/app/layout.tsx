import type { Metadata } from "next";

import TopNav from "@/components/TopNav";
import { AuthProvider } from "@/lib/AuthContext";
import { ChatResetProvider } from "@/lib/ChatResetContext";
import "./globals.css";

export const metadata: Metadata = {
  title: "PolicyLens",
  description: "Internal policy Q&A assistant",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      {/* System font stack (font-sans) instead of next/font/google's Inter --
          that fetches from Google's servers at compile time, which hangs the
          whole dev server ("The user aborted a request. Retrying...") on any
          network/firewall that blocks it. Zero network dependency this way. */}
      {/* h-screen + overflow-hidden (not min-h-screen) -- this is a fixed-height
          column, not a document that grows with content. Combined with min-h-0
          on every scrollable flex-1 region below, the browser's own window/
          document never scrolls; only the regions that explicitly want to
          (message list, history list) do, via their own overflow-y-auto. */}
      <body className="flex h-screen flex-col overflow-hidden bg-canvas font-sans text-ink antialiased">
        <AuthProvider>
          <ChatResetProvider>
            <TopNav />
            <main className="min-h-0 w-full flex-1">{children}</main>
          </ChatResetProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
