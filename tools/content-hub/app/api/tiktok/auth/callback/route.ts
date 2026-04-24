import { saveToken } from "@/lib/oauth-tokens";
import db from "@/lib/db";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const code = searchParams.get("code");
  const state = searchParams.get("state");
  const error = searchParams.get("error");

  if (error || !code || !state) {
    return new Response(`OAuth error: ${error ?? "missing code or state"}`, { status: 400 });
  }

  const clientKey = process.env.TIKTOK_CLIENT_KEY!;
  const clientSecret = process.env.TIKTOK_CLIENT_SECRET!;
  const redirectUri =
    process.env.TIKTOK_REDIRECT_URI ??
    "http://localhost:3000/api/tiktok/auth/callback";

  // Retrieve stored PKCE verifier
  const row = db
    .prepare("SELECT access_token FROM oauth_tokens WHERE platform = ?")
    .get(`tiktok_pkce_${state}`) as { access_token: string } | undefined;

  if (!row) {
    return new Response("PKCE state not found or expired", { status: 400 });
  }

  const codeVerifier = row.access_token;

  // Clean up temp verifier row
  db.prepare("DELETE FROM oauth_tokens WHERE platform = ?").run(`tiktok_pkce_${state}`);

  const res = await fetch("https://open.tiktokapis.com/v2/oauth/token/", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_key: clientKey,
      client_secret: clientSecret,
      code,
      grant_type: "authorization_code",
      redirect_uri: redirectUri,
      code_verifier: codeVerifier,
    }),
  });

  if (!res.ok) {
    return new Response(`Token exchange failed: ${await res.text()}`, { status: 500 });
  }

  const data = await res.json();
  saveToken("tiktok", {
    access_token: data.data?.access_token ?? data.access_token,
    refresh_token: data.data?.refresh_token ?? data.refresh_token,
    expires_in: data.data?.expires_in ?? data.expires_in,
  });

  return new Response(
    `<!DOCTYPE html><html><body style="font-family:sans-serif;padding:2rem">
      <h1>✅ TikTok connected!</h1>
      <p>You can close this tab and return to the app.</p>
    </body></html>`,
    { headers: { "Content-Type": "text/html" } },
  );
}
