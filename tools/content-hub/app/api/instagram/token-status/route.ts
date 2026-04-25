import { NextResponse } from "next/server";
import db from "@/lib/db";

/**
 * Reports days until the stored Instagram token expires.
 * If no row exists yet, falls back to "unknown" (env-only mode).
 * Used by /automation/run_ig_token_refresh.sh and any UI badge.
 */

interface TokenRow {
  platform: string;
  access_token: string;
  expires_at: string | null;
  updated_at: string | null;
}

export async function GET() {
  const row = db
    .prepare("SELECT * FROM oauth_tokens WHERE platform = ?")
    .get("instagram") as TokenRow | undefined;

  if (!row || !row.expires_at) {
    return NextResponse.json({
      platform: "instagram",
      known: false,
      days_until_expiry: null,
      warning: "No IG token row in oauth_tokens — POST /api/instagram/refresh-token to seed",
    });
  }

  const now = Date.now();
  const exp = new Date(row.expires_at).getTime();
  const days = Math.floor((exp - now) / (24 * 60 * 60 * 1000));
  const warn = days < 14;

  return NextResponse.json({
    platform: "instagram",
    known: true,
    expires_at: row.expires_at,
    updated_at: row.updated_at,
    days_until_expiry: days,
    warning: warn ? `IG token expires in ${days} days — refresh now` : null,
  });
}
