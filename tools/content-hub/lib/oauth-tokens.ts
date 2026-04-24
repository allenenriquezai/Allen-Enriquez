import db from "./db";

interface TokenRow {
  platform: string;
  access_token: string;
  refresh_token: string | null;
  expires_at: string | null;
}

export function saveToken(
  platform: "youtube" | "tiktok" | string,
  data: { access_token: string; refresh_token?: string; expires_in?: number },
): void {
  const expires_at = data.expires_in
    ? new Date(Date.now() + data.expires_in * 1000).toISOString()
    : null;
  db.prepare(`
    INSERT INTO oauth_tokens (platform, access_token, refresh_token, expires_at, updated_at)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(platform) DO UPDATE SET
      access_token = excluded.access_token,
      refresh_token = COALESCE(excluded.refresh_token, oauth_tokens.refresh_token),
      expires_at = excluded.expires_at,
      updated_at = excluded.updated_at
  `).run(
    platform,
    data.access_token,
    data.refresh_token ?? null,
    expires_at,
    new Date().toISOString(),
  );
}

export function deleteToken(platform: string): void {
  db.prepare("DELETE FROM oauth_tokens WHERE platform = ?").run(platform);
}

export async function getToken(platform: "youtube" | "tiktok"): Promise<string> {
  const row = db
    .prepare("SELECT * FROM oauth_tokens WHERE platform = ?")
    .get(platform) as TokenRow | undefined;

  if (!row) {
    throw new Error(
      `No token for ${platform}. Visit /api/${platform}/auth to connect.`,
    );
  }

  const now = Date.now();
  const expiresAt = row.expires_at ? new Date(row.expires_at).getTime() : null;
  const needsRefresh = expiresAt !== null && expiresAt - now < 60_000;

  if (!needsRefresh) return row.access_token;

  if (platform === "youtube") return refreshYouTubeToken(row);
  return refreshTikTokToken(row);
}

async function refreshYouTubeToken(row: TokenRow): Promise<string> {
  if (!row.refresh_token) throw new Error("No YouTube refresh token");
  const res = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "refresh_token",
      refresh_token: row.refresh_token,
      client_id: process.env.YOUTUBE_CLIENT_ID!,
      client_secret: process.env.YOUTUBE_CLIENT_SECRET!,
    }),
  });
  if (!res.ok) throw new Error(`YouTube token refresh failed: ${await res.text()}`);
  const data = await res.json();
  saveToken("youtube", { access_token: data.access_token, expires_in: data.expires_in });
  return data.access_token;
}

async function refreshTikTokToken(row: TokenRow): Promise<string> {
  if (!row.refresh_token) throw new Error("No TikTok refresh token");
  const res = await fetch("https://open.tiktokapis.com/v2/oauth/token/", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "refresh_token",
      refresh_token: row.refresh_token,
      client_key: process.env.TIKTOK_CLIENT_KEY!,
      client_secret: process.env.TIKTOK_CLIENT_SECRET!,
    }),
  });
  if (!res.ok) throw new Error(`TikTok token refresh failed: ${await res.text()}`);
  const data = await res.json();
  saveToken("tiktok", {
    access_token: data.data.access_token,
    refresh_token: data.data.refresh_token,
    expires_in: data.data.expires_in,
  });
  return data.data.access_token;
}
