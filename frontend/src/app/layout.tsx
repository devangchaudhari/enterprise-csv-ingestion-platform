import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OmniRetail Enterprise Data Hub & Orchestration Engine",
  description: "Next-Generation Enterprise Data Integration, Quality Reconciliation, and Azure Workflow Orchestration Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 antialiased selection:bg-sky-500 selection:text-white">
        {children}
      </body>
    </html>
  );
}
