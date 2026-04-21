"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Lightbulb,
  FileText,
  Calendar,
  FolderOpen,
  BarChart3,
  Inbox,
  BookOpen,
  Rss,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/ideation", label: "Ideation", icon: Lightbulb },
  { href: "/scripts", label: "Scripts", icon: FileText },
  { href: "/calendar", label: "Calendar", icon: Calendar },
  { href: "/library", label: "Library", icon: FolderOpen },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/inbox", label: "Inbox", icon: Inbox },
  { href: "/learning", label: "Learning", icon: BookOpen },
  { href: "/creator-feed", label: "Creator Feed", icon: Rss },
];

export function TabNav() {
  const pathname = usePathname();
  return (
    <nav className="flex-1 px-3 py-4 flex flex-col gap-1.5">
      {NAV.map((item) => {
        const active =
          pathname === item.href || pathname?.startsWith(item.href + "/");
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "group flex items-center gap-3 px-3 py-2.5 text-sm transition-all",
              "ae-pill",
              active
                ? "ae-pill-active"
                : "text-muted-foreground hover:text-foreground",
            )}
            style={{
              fontFamily: "var(--font-roboto-mono)",
              letterSpacing: "0.04em",
              color: active ? "var(--brand)" : undefined,
            }}
          >
            <span
              className={cn(
                "inline-flex items-center justify-center h-7 w-7 rounded-md transition-colors",
                active
                  ? "bg-[color:var(--brand)]/15"
                  : "bg-[color:var(--muted)]/40 group-hover:bg-[color:var(--brand)]/10",
              )}
              style={active ? { boxShadow: "0 0 14px rgba(2,179,233,0.35)" } : undefined}
            >
              <Icon className="h-3.5 w-3.5" />
            </span>
            <span className="text-[0.78rem] font-medium uppercase">
              {item.label}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
