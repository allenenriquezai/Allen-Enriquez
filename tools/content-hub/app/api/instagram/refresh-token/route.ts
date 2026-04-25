import { NextResponse } from "next/server";
import db from "@/lib/db";

/**
 * Refresh Instagram (Facebook Graph API) long-lived user token.
 *
 * Allen's IG flow uses graph.facebook.com/v25.0 (see app/api/instagram/publish/route.ts),
 * so this hits the FB Graph long-lived token exchange. Long-lived tokens last ~60 days
 * and can be re-exchanged any time after their first 24h to get a fresh 60-day token.
 *
 * Source token resolution:
 *   1) oauth_tokens row (platform = "instagram") — preferred once seeded.
 *   2) INSTAGRAM_USER_TOKEN env var — fallback / first-run seed.
 *
 * After a successful refresh we upsert the new token into oauth_tokens so future
 * refreshes chain off the DB row (env var stays as cold-start fallback).
 *
 * Required env: FACEBOOK_APP_ID (or INSTAGRAM_APP_ID), FACEBOOK_APP_SECRET.
 * No auth on the route — Allen-only Railway app.
 */

const FB_BASE = "https://graph.facebook.com/v25.0";
const SIXTY_DAYS_MS = 60 * 24 * 60 * 60 * 1000;

interface TokenRow {
  platform: string;
  access_token: string;
  refresh_token: string | null;
  expires_at: string | null;
}

export async function POST() {
  try {
    const appId = process.env.FACEBOOK_APP_ID || process.env.INSTAGRAM_APP_ID;
    const appSecret = process.env.FACEBOOK_APP_SECRET;
    if (!appSecret) {
      return NextResponse.json(
        { error: "Missing FACEBOOK_APP_SECRET" },
        { status: 500 },
      );
    }
    if (!appId) {
      return NextResponse.json(
        { error: "Missing FACEBOOK_APP_ID (or INSTAGRAM_APP_ID)" },
        { status: 500 },
      );
    }

    const row = db
      .prepare("SELECT * FROM oauth_tokens WHERE platform = ?")
      .get("instagram") as TokenRow | undefined;

    const currentToken = row?.access_token || process.env.INSTAGRAM_USER_TOKEN;
    if (!currentToken) {
      return NextResponse.json(
        {
          error:
            "No current IG token in oauth_tokens or INSTAGRAM_USER_TOKEN env",
        },
        { status: 500 },
      );
    }

    const url = new URL(`${FB_BASE}/oauth/access_token`);
    url.searchParams.set("grant_type", "fb_exchange_token");
    url.searchParams.set("client_id", appId);
    url.searchParams.set("client_secret", appSecret);
    url.searchParams.set("fb_exchange_token", currentToken);

    const res = await fetch(url.toString(), { cache: "no-store" });
    const text = await res.text();
    if (!res.ok) {
      return NextResponse.json(
        { error: "FB token refresh failed", detail: text },
        { status: 500 },
      );
    }

    let data: { access_token?: string; expires_in?: number };
    try {
      data = JSON.parse(text);
    } catch {
      return NextResponse.json(
        { error: "FB returned non-JSON", detail: text },
        { status: 500 },
      );
    }

    if (!data.access_token) {
      return NextResponse.json(
        { error: "FB response missing access_token", detail: text },
        { status: 500 },
      );
    }

    const expiresMs = (data.expires_in ?? 0) * 1000 || SIXTY_DAYS_MS;
    const expiresAt = new Date(Date.now() + expiresMs).toISOString();
    const now = new Date().toISOString();

    db.prepare(
      `INSERT INTO oauth_tokens (platform, access_token, refresh_token, expires_at, updated_at)
       VALUES (?, ?, NULL, ?, ?)
       ON CONFLICT(platform) DO UPDATE SET
         access_token = excluded.access_token,
         expires_at = excluded.expires_at,
         updated_at = excluded.updated_at`,
    ).run("instagram", data.access_token, expiresAt, now);

    return NextResponse.json({
      refreshed: true,
      expires_at: expiresAt,
      seeded_from_env: !row,
    });
  } catch (err) {
    return NextResponse.json(
      { error: "Refresh threw", detail: String(err) },
      { status: 500 },
    );
  }
}
