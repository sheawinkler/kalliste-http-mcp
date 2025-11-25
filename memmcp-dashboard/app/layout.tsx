import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "memMCP Dashboard",
  description: "Operator console for the memory MCP service",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-950 text-slate-100 min-h-screen">
        <header className="border-b border-slate-800 p-4">
          <h1 className="text-2xl font-semibold">memMCP Dashboard</h1>
          <p className="text-sm text-slate-400">
            Live window into the memory bank, orchestrator, and MCP stack
          </p>
        </header>
        <main className="p-4 max-w-5xl mx-auto">{children}</main>
      </body>
    </html>
  );
}
