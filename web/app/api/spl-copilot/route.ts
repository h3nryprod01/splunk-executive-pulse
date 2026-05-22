import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";

// Serves SPL Copilot scenarios computed by the Python pipeline
// (spl_copilot/export_demo.py -> web/public/spl_copilot/scenarios.json).
// Returns 404 when none exists so the client falls back to mock data.
export async function GET() {
  const file = path.join(process.cwd(), "public", "spl_copilot", "scenarios.json");
  try {
    const raw = await fs.readFile(file, "utf-8");
    return NextResponse.json(JSON.parse(raw), {
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json({ error: "no scenarios exported" }, { status: 404 });
  }
}
