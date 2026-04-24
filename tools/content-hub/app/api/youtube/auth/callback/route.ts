import { saveToken } from "@/lib/oauth-tokens";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const code = searchParams.get("code");
  const error = searchParams.get("error");

  if (error || !code) {
    return new Response(`OAuth error: ${error ?? "missing code"}`, { status: 400 });
  }

  const clientId = process.env.YOUTUBE_CLIENT_ID!;
  const clientSecret = process.env.YOUTUBE_CLIENT_SECRET!;
  const redirectUri =
    process.env.YOUTUBE_REDIRECT_URI ??
    "http://localhost:3000/api/youtube/auth/callback";

  const res = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      code,
      client_id: clientId,
      client_secret: clientSecret,
      redirect_uri: redirectUri,
    }),
  });

  if (!res.ok) {
    return new Response(`Token exchange failed: ${await res.text()}`, { status: 500 });
  }

  const data = await res.json();
  saveToken("youtube", {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    expires_in: data.expires_in,
  });

  return new Response(
    `<!DOCTYPE html><html><body style="font-family:sans-serif;padding:2rem">
      <h1>YouTube connected!</h1>
      <p>You can close this tab and return to the app.</p>
    </body></html>`,
    { headers: { "Content-Type": "text/html" } },
  );
}
