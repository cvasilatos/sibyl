import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sibyl - AI Research Paper Review",
  description: "AI-Powered Research Paper Review System using local LLMs",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
