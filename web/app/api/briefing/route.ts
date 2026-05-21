import { NextRequest, NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";

// Serves a briefing computed by the Python pipeline
// (orchestration/export_briefings.py -> web/public/briefings/<persona>-latest.json).
// Returns 404 when none exists so the client falls back to mock data.
export async function GET(req: NextRequest) {
  const persona = (req.nextUrl.searchParams.get("persona") || "CEO").toLowerCase();
  if (!/^[a-z]+$/.test(persona)) {
    return NextResponse.json({ error: "invalid persona" }, { status: 400 });
  }

  const file = path.join(process.cwd(), "public", "briefings", `${persona}-latest.json`);
  try {
    const raw = await fs.readFile(file, "utf-8");
    return NextResponse.json(JSON.parse(raw), {
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json({ error: "no briefing for persona" }, { status: 404 });
  }
}
