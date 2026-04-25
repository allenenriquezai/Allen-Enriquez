"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Calendar,
  Clapperboard,
  Sparkles,
  FolderOpen,
  BarChart3,
  MessageSquare,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/calendar", label: "Calendar", icon: Calendar },
  { href: "/scripts", label: "Studio", icon: Clapperboard, matchPaths: ["/scripts", "/ideation"] },
  { href: "/inspiration", label: "Inspiration", icon: Sparkles },
  { href: "/library", label: "Library", icon: FolderOpen },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/inbox", label: "Inbox", icon: MessageSquare },
];

const MOBILE_NAV = [
  { href: "/calendar", label: "Calendar", icon: Calendar },
  { href: "/scripts", label: "Studio", icon: Clapperboard, matchPaths: ["/scripts", "/ideation"] },
  { href: "/inspiration", label: "Inspire", icon: Sparkles },
  { href: "/library", label: "Library", icon: FolderOpen },
  { href: "/analytics", label: "Stats", icon: BarChart3 },
  { href: "/inbox", label: "Inbox", icon: MessageSquare },
];

export function TabNav() {
  const pathname = usePathname();
  return (
    <nav className="flex-1 px-3 py-4 flex flex-col gap-1.5">
      {NAV.map((item) => {
        const matches = item.matchPaths ?? [item.href];
        const active = matches.some(
          (p) => pathname === p || pathname?.startsWith(p + "/"),
        );
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

export function MobileBottomNav() {
  const pathname = usePathname();
  return (
    <nav className="fixed bottom-0 inset-x-0 z-50 flex md:hidden border-t border-sidebar-border bg-sidebar">
      {MOBILE_NAV.map((item) => {
        const matches = item.matchPaths ?? [item.href];
        const active = matches.some(
          (p) => pathname === p || pathname?.startsWith(p + "/"),
        );
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex-1 flex flex-col items-center justify-center gap-1 py-2.5 text-[10px] font-medium uppercase transition-colors",
              active
                ? "text-[color:var(--brand)]"
                : "text-muted-foreground hover:text-foreground",
            )}
            style={{ fontFamily: "var(--font-roboto-mono)", letterSpacing: "0.04em" }}
          >
            <Icon
              className="h-5 w-5"
              style={active ? { filter: "drop-shadow(0 0 6px rgba(2,179,233,0.6))" } : undefined}
            />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
