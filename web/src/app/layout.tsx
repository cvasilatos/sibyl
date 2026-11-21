import type { Metadata } from "next";
import "./globals.css";
import NavTabs from "@/components/NavTabs";
import { Toaster } from "@/components/ui/toaster";
import { GlobalDownloadProgress } from "@/features/models/GlobalDownloadProgress";
import Providers from "./providers";

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
        <Providers>
          <GlobalDownloadProgress />
          <div className="flex min-h-screen flex-col bg-background">
            <header className="border-b bg-card px-4 py-4 md:px-8">
              <div className="mb-4 flex items-center gap-3">
                <span className="text-3xl">🔮</span>
                <div>
                  <h1 className="text-xl font-bold leading-tight">Sibyl</h1>
                  <p className="text-sm text-muted-foreground">AI-Powered Research Paper Review</p>
                </div>
              </div>
              <NavTabs />
            </header>
            <main className="flex-1 space-y-6 px-4 py-6 md:px-8">{children}</main>
            <footer className="border-t px-4 py-3 text-center">
              <p className="text-xs text-muted-foreground">Powered by local open-source LLMs • Privacy-first • Zero-cost</p>
            </footer>
          </div>
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}
