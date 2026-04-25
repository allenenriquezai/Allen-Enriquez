"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const TABS = [
  { href: "/scripts", label: "Scripts" },
  { href: "/ideation", label: "Ideation" },
];

export function StudioSubNav() {
  const pathname = usePathname();
  return (
    <div className="flex items-center gap-1 border-b border-sidebar-border mb-4">
      {TABS.map((t) => {
        const active = pathname === t.href || pathname?.startsWith(t.href + "/");
        return (
          <Link
            key={t.href}
            href={t.href}
            className={cn(
              "px-4 py-2 text-sm font-medium uppercase border-b-2 transition-colors",
              active
                ? "border-[color:var(--brand)] text-[color:var(--brand)]"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
            style={{
              fontFamily: "var(--font-roboto-mono)",
              letterSpacing: "0.06em",
            }}
          >
            {t.label}
          </Link>
        );
      })}
    </div>
  );
}
