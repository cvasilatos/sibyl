"use client";

import { BookOpen, ClipboardList, FileText, type LucideIcon, Monitor, Settings } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const TABS: { href: string; label: string; icon: LucideIcon }[] = [
  { href: "/review", label: "Review Paper", icon: FileText },
  { href: "/forms", label: "Review Forms", icon: ClipboardList },
  { href: "/library", label: "Library", icon: BookOpen },
  { href: "/models", label: "Models", icon: Settings },
  { href: "/gpu", label: "GPU", icon: Monitor },
];

export default function NavTabs() {
  const pathname = usePathname();
  return (
    <nav className="flex gap-6 sm:gap-12">
      {TABS.map(({ href, label, icon: Icon }) => {
        const active = pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "relative px-2 pb-6 text-sm font-medium transition-colors",
              active ? "text-primary" : "text-muted-foreground hover:text-foreground",
            )}
          >
            <div className="flex items-center gap-2">
              <Icon className="h-4 w-4" />
              <span>{label}</span>
            </div>
            {active && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />}
          </Link>
        );
      })}
    </nav>
  );
}
