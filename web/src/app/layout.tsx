import type { Metadata } from "next";
import "./globals.css";
import { GlobalDownloadProgress } from "@/components/GlobalDownloadProgress";
import { Toaster } from "@/components/ui/toaster";
import { DownloadProvider } from "@/lib/download-context";

export const metadata: Metadata = {
  title: "Sibyl - AI Research Paper Review",
  description: "AI-Powered Research Paper Review System using local LLMs",
  icons: {
    icon: "app/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <DownloadProvider>
          <GlobalDownloadProgress />
          {children}
          <Toaster />
        </DownloadProvider>
      </body>
    </html>
  );
}
