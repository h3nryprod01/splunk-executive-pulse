# Video recording guide — step by step

Target: a **≤ 3-minute** demo, 1080p, burned-in captions, public on YouTube/Vimeo/Youku.
The 60-second hero is the **real ElevenLabs audio** we already generated.

## 0. Compliance (read first — these are hard rules)
- Public on **YouTube, Vimeo, or Youku** only; put the link on the Devpost form.
- **No unlicensed music, trademarks, or copyrighted material.** Use royalty-free music
  (Pixabay Music, YouTube Audio Library, Uppbeat free tier) and keep the receipt/source.
- Don't use the **Splunk logo** unless it's from an official brand kit — a plain text
  wordmark "Splunk Executive Pulse" is safe.
- Our narration audio (`web/public/audio/*.mp3`) is ElevenLabs-generated under your
  account — fine to use. Avoid real customer/company names (our data is synthetic).

## 1. Prep the live demo (once)
```bash
# from repo root
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python business_context/seed_data/generate_customers.py
set -a && source .env && set +a
python orchestration/export_briefings_live.py --all --audio   # real prose + 5 mp3s
cd web && npm install && npm run dev                          # http://localhost:3000
```
Confirm the dashboard shows live data (header quote like "We lost $11,748…") and the
audio files exist in `web/public/audio/`.

## 2. What to screen-record (capture raw clips, edit later)
Use macOS screen recording (**Cmd+Shift+5**, record selected area at the display's native
res; set a 16:9 region). Record these as separate clips:

1. **Dashboard hero (CEO)** — load `localhost:3000`, slowly scroll the briefing: header
   quote → KPI cards → Story cards → hover a "Receipts" citation chip. ~20s.
2. **Persona switch** — click **CEO → CISO**; show the headline flip (revenue → security)
   and the stories reorder. Then CFO. ~15s. This is the "same data, different lens" beat.
3. **Pipeline proof (terminal)** — record:
   ```bash
   python orchestration/graph_e2e_demo.py --persona CISO   # status: succeeded, 7 stages
   python orchestration/drilldown_demo.py                  # NL question -> SPL (AI Assistant)
   ```
4. **Architecture** — open `ARCHITECTURE.md` (VS Code Markdown preview or paste the Mermaid
   into mermaid.live) and slowly pan the high-level diagram. ~10s.

## 3. Audio
- For the 60-second hero, **import `web/public/audio/pulse-2026-05-21-ceo-norm.mp3`
  directly into the editor as the voice track** (cleaner than recording speaker output),
  and sync the dashboard scroll/persona clips under it.
- For the personalization beat, drop ~8s of the **CISO** mp3 to prove each persona gets
  its own audio.
- Music bed: royalty-free piano, volume ~ -22 dB under the voice.

## 4. Edit to the script
Follow [DEMO_SCRIPT.md](DEMO_SCRIPT.md) scene timings (Problem → Solution → Demo →
How it works → Close). Tools: CapCut, iMovie, or Descript (Descript auto-generates
captions and lets you edit video by editing text).

- **Burn in captions** (judges watch muted). CapCut/Descript auto-caption, then review.
- Color/zoom: Splunk dark `#0a0e1a` background, gold `#f5b800` accent for title cards.
- Add lower-thirds: "Splunk MCP Server", "Splunk Hosted Models", "AI Assistant for SPL",
  "AI Toolkit (MLTK)" when the architecture shows — makes the 4 capabilities explicit.

## 5. Export & publish
- Export **1080p (1920×1080) MP4, H.264**, ≤ 3:00.
- Upload to YouTube as **Public or Unlisted** (Unlisted is allowed and link-shareable).
- Title: "Splunk Executive Pulse — Splunk Agentic Ops Hackathon 2026".
- Put the link in: the Devpost submission form **and** the README badge
  (replace the `[▶ Watch demo]` placeholder).

## 6. 30-second shot list (if you're short on time)
1. (0:00) Title card + one-line problem.
2. (0:08) Dashboard CEO, hit play → 12–15s of real audio over a scroll.
3. (0:22) Click to CISO → headline flips to security. "Same data, different lens."
4. (0:35) Terminal: `graph_e2e_demo.py` → `status: succeeded`.
5. (0:45) Architecture diagram pan + 4 capability lower-thirds.
6. (0:55) Repo URL + tagline. Done.
