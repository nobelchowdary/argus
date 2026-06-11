import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Argus — AML Investigation Agent",
  description:
    "An AML investigation agent that drafts SARs from evidence, not imagination.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[var(--background)] text-[var(--foreground)] antialiased">
        {children}
      </body>
    </html>
  );
}
