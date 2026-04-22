import { NextResponse } from "next/server";
import { seedLearning } from "@/scripts/seed-learning";

// POST /api/learning/reseed — re-run the learning importer (idempotent upsert).
export async function POST() {
  try {
    const result = seedLearning();
    return NextResponse.json({ ok: true, ...result });
  } catch (err) {
    return NextResponse.json(
      { error: (err as Error).message },
      { status: 500 },
    );
  }
}
