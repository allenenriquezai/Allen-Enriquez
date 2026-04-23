"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";

const TABS = [
  { key: "calendar", label: "Calendar", href: "/calendar" },
  { key: "queue", label: "Post Queue", href: "/calendar?tab=queue" },
] as const;

export function CalendarTabSwitcher({ active }: { active: "calendar" | "queue" }) {
  return (
    <div className="flex items-center gap-1 rounded-lg border border-border bg-muted/30 p-1">
      {TABS.map((tab) => (
        <Link
          key={tab.key}
          href={tab.href}
          className={cn(
            "px-3 py-1 rounded-md text-sm font-medium transition-colors",
            active === tab.key
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {tab.label}
        </Link>
      ))}
    </div>
  );
}
