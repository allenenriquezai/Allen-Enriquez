import type { Metadata } from "next";
import { Montserrat, Roboto_Mono } from "next/font/google";
import "./globals.css";
import { TabNav, MobileBottomNav } from "@/components/tab-nav";
import { AeMonogram } from "@/components/ae-monogram";

const montserrat = Montserrat({
  variable: "--font-montserrat",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  display: "swap",
});

const robotoMono = Roboto_Mono({
  variable: "--font-roboto-mono",
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  display: "swap",
});

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Content Hub — AE",
  description: "Allen's unified content operations dashboard.",
};

function formatToday() {
  const d = new Date();
  return d.toLocaleDateString("en-US", {
    weekday: "short",
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`dark ${montserrat.variable} ${robotoMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex">
        <aside className="hidden md:flex w-64 shrink-0 border-r border-sidebar-border bg-sidebar text-sidebar-foreground flex-col">
          <div className="px-5 py-6 border-b border-sidebar-border">
            <div className="flex items-center gap-3">
              <AeMonogram size={40} />
              <div className="flex flex-col leading-tight">
                <span
                  className="ae-mono-label"
                  style={{ color: "var(--light-grey)" }}
                >
                  Enriquez OS
                </span>
                <span className="text-sm font-semibold tracking-tight">
                  Content Hub
                </span>
              </div>
            </div>
          </div>
          <TabNav />
          <div className="px-5 py-4 border-t border-sidebar-border">
            <div className="ae-mono-label">Phase 1</div>
            <p className="text-xs text-muted-foreground pt-1 font-light">
              Organization layer. Posting + auto-analytics come in Phase 2.
            </p>
          </div>
        </aside>
        <div className="flex-1 flex flex-col min-w-0">
          <header className="border-b border-border px-8 py-4 flex items-center justify-between">
            <div className="flex items-baseline gap-3">
              <h1
                className="text-base font-semibold tracking-tight"
                style={{ fontFamily: "var(--font-roboto-mono)", letterSpacing: "0.04em" }}
              >
                CONTENT HUB
              </h1>
              <span className="ae-mono-label">v1 · local</span>
            </div>
            <span className="ae-mono-label" style={{ color: "var(--brand)" }}>
              {formatToday()}
            </span>
          </header>
          <main className="flex-1 p-8 overflow-auto pb-16 md:pb-0">{children}</main>
        </div>
        <MobileBottomNav />
      </body>
    </html>
  );
}
