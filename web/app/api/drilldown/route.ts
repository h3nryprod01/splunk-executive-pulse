import { NextRequest, NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";

// Executive drill-down: a plain-English question -> SPL, via the Splunk AI
// Assistant for SPL. Mirrors agents/common/splunk_ai/spl_assistant.py: when a
// live Assistant endpoint is configured it would be called; otherwise the
// deterministic offline phrasebook (web/public/spl-phrasebook.json) is used so
// the demo runs keyless.

interface Entry {
  keywords: string[];
  spl: string;
  explanation: string;
}

export async function GET(req: NextRequest) {
  const q = (req.nextUrl.searchParams.get("q") || "").trim();
  if (!q) {
    return NextResponse.json({ error: "missing q" }, { status: 400 });
  }

  const file = path.join(process.cwd(), "public", "spl-phrasebook.json");
  let book: Entry[] = [];
  try {
    book = JSON.parse(await fs.readFile(file, "utf-8"));
  } catch {
    return NextResponse.json({ error: "phrasebook unavailable" }, { status: 503 });
  }

  const text = q.toLowerCase();
  const hit = book.find((e) => e.keywords.every((k) => text.includes(k)));
  if (hit) {
    return NextResponse.json({
      intent: q,
      spl: hit.spl,
      explanation: hit.explanation,
      source: "splunk-ai-assistant (offline)",
      confidence: 0.6,
    });
  }

  // Generic fallback — keyword search, matching the Python behavior.
  const terms = (text.match(/[a-z0-9_]+/g) || []).filter((t) => t.length > 2).slice(0, 5);
  return NextResponse.json({
    intent: q,
    spl: `search index=* ${terms.join(" ")} | head 100`,
    explanation: "Generic keyword search (no template matched).",
    source: "splunk-ai-assistant (offline)",
    confidence: 0.3,
  });
}
