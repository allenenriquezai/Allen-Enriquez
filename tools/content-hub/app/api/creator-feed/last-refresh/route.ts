import { NextResponse } from "next/server";
import db from "@/lib/db";

export async function GET() {
  const row = db
    .prepare(
      "SELECT MAX(fetched_at) AS last_fetched_at, COUNT(*) AS total FROM creator_posts"
    )
    .get() as { last_fetched_at: string | null; total: number };
  return NextResponse.json(row);
}
