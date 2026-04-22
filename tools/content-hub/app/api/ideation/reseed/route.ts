import { NextResponse } from "next/server";
import { seedIdeation } from "@/scripts/seed-ideation";

// POST /api/ideation/reseed — re-runs the drafts + research seeder.
// Idempotent: upserts by (title, batch).
export async function POST() {
  try {
    const result = seedIdeation();
    return NextResponse.json({ ok: true, ...result });
  } catch (err) {
    console.error("[reseed] failed:", err);
    return NextResponse.json(
      { ok: false, error: (err as Error).message ?? "seed failed" },
      { status: 500 },
    );
  }
}
