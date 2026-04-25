import { NextResponse } from "next/server";
import db from "@/lib/db";

type Row = {
  id: number;
  idea_id: number;
  variant: string;
  body: string;
  word_count: number | null;
  updated_at: string;
  idea_title: string;
  idea_hook: string | null;
  idea_pillar: string | null;
};

// GET /api/scripts/list?variant=reel|youtube — script + idea metadata for pickers
export async function GET(req: Request) {
  const url = new URL(req.url);
  const variant = url.searchParams.get("variant"); // optional filter

  const sql = `
    SELECT
      s.id, s.idea_id, s.variant, s.body, s.word_count, s.updated_at,
      i.title  AS idea_title,
      i.hook   AS idea_hook,
      i.pillar AS idea_pillar
    FROM scripts s
    JOIN ideas i ON i.id = s.idea_id
    WHERE s.variant IN ('reel', 'youtube')
      ${variant ? "AND s.variant = ?" : ""}
    ORDER BY s.updated_at DESC
  `;
  const rows = (variant ? db.prepare(sql).all(variant) : db.prepare(sql).all()) as Row[];

  return NextResponse.json({ scripts: rows });
}
