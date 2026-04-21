import db from "@/lib/db";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

type Post = {
  id: number;
  post_id: string;
  creator: string;
  platform: string;
  url: string;
  title: string | null;
  description: string | null;
  thumbnail_url: string | null;
  posted_at: string | null;
  view_count: number | null;
  like_count: number | null;
  comment_count: number | null;
  duration_sec: number | null;
  transcript: string | null;
  hook: string | null;
  topic: string | null;
  why_it_works: string | null;
  fetched_at: string;
};

function fmtNum(n: number | null): string {
  if (n == null) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function fmtDate(s: string | null): string {
  if (!s) return "—";
  try {
    return new Date(s).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return s;
  }
}

export default async function CreatorFeedPage() {
  const posts = db
    .prepare(
      `SELECT id, post_id, creator, platform, url, title, description,
              thumbnail_url, posted_at, view_count, like_count, comment_count,
              duration_sec, transcript, hook, topic, why_it_works, fetched_at
       FROM creator_posts
       ORDER BY COALESCE(posted_at, fetched_at) DESC
       LIMIT 100`,
    )
    .all() as Post[];

  const creators = [...new Set(posts.map((p) => p.creator))];

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Creator Feed</h1>
        <p className="text-sm text-muted-foreground">
          {posts.length} post{posts.length === 1 ? "" : "s"} · {creators.length} creator{creators.length === 1 ? "" : "s"}
        </p>
      </div>

      {posts.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-sm text-muted-foreground">
            No creator posts yet. Run <code className="text-[var(--brand)]">python3 tools/creator_feed.py</code> to fetch.
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {posts.map((p) => (
            <Card key={p.id} className="overflow-hidden">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge variant="outline">{p.creator}</Badge>
                    <Badge variant="secondary">{p.platform}</Badge>
                    <span className="text-xs text-muted-foreground">
                      {fmtDate(p.posted_at)}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground shrink-0">
                    <span>👁 {fmtNum(p.view_count)}</span>
                    <span>❤ {fmtNum(p.like_count)}</span>
                    <span>💬 {fmtNum(p.comment_count)}</span>
                  </div>
                </div>
                <CardTitle className="text-base leading-snug pt-2">
                  <a
                    href={p.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-[var(--brand)]"
                  >
                    {p.title || p.hook || p.post_id}
                  </a>
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0 flex gap-4">
                {p.thumbnail_url && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={p.thumbnail_url}
                    alt=""
                    className="w-28 h-auto rounded-md border border-border shrink-0 object-cover"
                  />
                )}
                <div className="flex-1 flex flex-col gap-2 text-sm min-w-0">
                  {p.hook && (
                    <div>
                      <div className="ae-mono-label pb-1">Hook</div>
                      <p className="leading-snug">{p.hook}</p>
                    </div>
                  )}
                  {p.topic && (
                    <div>
                      <div className="ae-mono-label pb-1">Topic</div>
                      <p className="text-muted-foreground leading-snug">
                        {p.topic}
                      </p>
                    </div>
                  )}
                  {p.why_it_works && (
                    <div>
                      <div className="ae-mono-label pb-1" style={{ color: "var(--brand)" }}>
                        Why it works
                      </div>
                      <p className="text-muted-foreground leading-snug">
                        {p.why_it_works}
                      </p>
                    </div>
                  )}
                  {p.transcript && (
                    <details className="mt-2">
                      <summary className="ae-mono-label cursor-pointer hover:text-[var(--brand)]">
                        Transcript
                      </summary>
                      <pre className="mt-2 whitespace-pre-wrap text-xs text-muted-foreground leading-relaxed font-sans max-h-64 overflow-auto">
                        {p.transcript}
                      </pre>
                    </details>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
