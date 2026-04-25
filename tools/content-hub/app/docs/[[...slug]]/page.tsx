import fs from "node:fs";
import path from "node:path";
import { notFound } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export const dynamic = "force-static";

const DOCS_DIR = path.join(process.cwd(), "docs");

const FILES = [
  { slug: "", file: "README.md", title: "Index" },
  { slug: "content-workflow", file: "CONTENT-WORKFLOW.md", title: "Content Workflow" },
  { slug: "content-hub", file: "CONTENT-HUB.md", title: "Content Hub Architecture" },
];

function findDoc(slug: string | undefined) {
  const want = slug ?? "";
  return FILES.find((f) => f.slug === want);
}

export default async function DocsPage({
  params,
}: {
  params: Promise<{ slug?: string[] }>;
}) {
  const { slug } = await params;
  const key = (slug?.[0] ?? "").toLowerCase();
  const doc = findDoc(key);
  if (!doc) notFound();

  const fullPath = path.join(DOCS_DIR, doc.file);
  if (!fs.existsSync(fullPath)) notFound();
  const content = fs.readFileSync(fullPath, "utf8");

  return (
    <div className="flex gap-8">
      <aside className="w-56 shrink-0 hidden lg:block">
        <div
          className="ae-mono-label pb-2"
          style={{ color: "var(--brand)", letterSpacing: "0.08em" }}
        >
          DOCS
        </div>
        <nav className="flex flex-col gap-1 text-sm">
          {FILES.map((f) => (
            <Link
              key={f.slug || "_root"}
              href={f.slug ? `/docs/${f.slug}` : "/docs"}
              className={
                key === f.slug
                  ? "text-[color:var(--brand)] font-medium"
                  : "text-muted-foreground hover:text-foreground"
              }
            >
              {f.title}
            </Link>
          ))}
        </nav>
      </aside>
      <article className="prose prose-invert max-w-3xl flex-1">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </article>
    </div>
  );
}
