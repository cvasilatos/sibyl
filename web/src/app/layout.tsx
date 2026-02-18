import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sibyl - AI Research Paper Review | NYU Center for Cybersecurity",
  description: "AI-Powered Research Paper Review System using local LLMs - Developed by NYU Center for Cybersecurity, MoMA Group (Mobile Security and Communications Systems)",
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
