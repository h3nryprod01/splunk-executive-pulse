import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Splunk Executive Pulse",
  description: "From data to decisions, in 3 minutes.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
