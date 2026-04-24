import { NextResponse } from "next/server";
import { createHash, randomBytes } from "crypto";
import db from "@/lib/db";

function generateCodeVerifier(): string {
  return randomBytes(32).toString("base64url");
}

function generateCodeChallenge(verifier: string): string {
  return createHash("sha256").update(verifier).digest("base64url");
}

export async function GET() {
  const clientKey = process.env.TIKTOK_CLIENT_KEY;
  if (!clientKey) {
    return NextResponse.json({ error: "TIKTOK_CLIENT_KEY not set. Register a TikTok developer app first." }, { status: 500 });
  }

  const redirectUri =
    process.env.TIKTOK_REDIRECT_URI ??
    "http://localhost:3000/api/tiktok/auth/callback";

  const codeVerifier = generateCodeVerifier();
  const codeChallenge = generateCodeChallenge(codeVerifier);
  const state = randomBytes(16).toString("hex");

  // Store verifier keyed by state (reuse oauth_tokens table with temp platform key)
  db.prepare(`
    INSERT INTO oauth_tokens (platform, access_token, updated_at)
    VALUES (?, ?, ?)
    ON CONFLICT(platform) DO UPDATE SET access_token = excluded.access_token, updated_at = excluded.updated_at
  `).run(`tiktok_pkce_${state}`, codeVerifier, new Date().toISOString());

  const scopes = [
    "user.info.basic",
    "video.publish",
    "video.list",
    "comment.list",
    "comment.list.manage",
  ];

  const url = new URL("https://www.tiktok.com/v2/auth/authorize/");
  url.searchParams.set("client_key", clientKey);
  url.searchParams.set("scope", scopes.join(","));
  url.searchParams.set("response_type", "code");
  url.searchParams.set("redirect_uri", redirectUri);
  url.searchParams.set("state", state);
  url.searchParams.set("code_challenge", codeChallenge);
  url.searchParams.set("code_challenge_method", "S256");

  return NextResponse.redirect(url.toString());
}
