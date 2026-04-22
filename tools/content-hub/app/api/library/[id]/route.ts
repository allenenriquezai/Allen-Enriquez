import { NextRequest } from "next/server";
import { patchAssetRow } from "../route";

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const body = await req.json();
  return patchAssetRow(Number(id), body);
}
