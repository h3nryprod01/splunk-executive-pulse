import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";

// Serves the SOC Triage incident report computed by the Python pipeline
// (soc_triage/export_demo.py -> web/public/soc_triage/incident.json).
// Returns 404 when none exists so the client falls back to mock data.
export async function GET() {
  const file = path.join(process.cwd(), "public", "soc_triage", "incident.json");
  try {
    const raw = await fs.readFile(file, "utf-8");
    return NextResponse.json(JSON.parse(raw), {
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json({ error: "no incident exported" }, { status: 404 });
  }
}
