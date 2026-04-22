import { NextRequest } from "next/server";
import { patchScheduleRow } from "../route";

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const body = await req.json();
  return patchScheduleRow(Number(id), body);
}
