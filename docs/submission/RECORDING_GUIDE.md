# Recording Guide — Splunk Executive Pulse demo video

Target: **2:35–2:50** demo (cap is 3:00). Audio = `web/public/audio/pulse-2026-05-21-cto-norm.mp3` (152.1s). The first 2:32 of video matches the audio script. The last 15–20s is a silent tour of SPL Copilot + SOC Triage.

---

## URLs to record

App is already running. Pick one:

- **Local** — `http://localhost:3333/` (best quality, no jitter)
- **Public tunnel** — `https://weight-asset-outer-arguments.trycloudflare.com/` (test the live URL works; only useful if you want to share it for judges to click)

Both serve the same Next.js dev server on port 3333.

Three pages you'll visit:

| Path | What it shows |
|------|---------------|
| `/` | Executive dashboard — persona switcher (CEO/CFO/**CTO**/CISO/COO), audio player, story cards, decisions, drill-down |
| `/spl-copilot` | NL → SPL with self-critique loop |
| `/soc-triage` | Autonomous alert investigation |

---

## Setup before recording

1. **Browser**: Chrome/Brave, **1440×900** window. (Cmd+Shift+R to hard-refresh once.)
2. **Recorder**:
   - macOS QuickTime → File → New Screen Recording (free)
   - or Screen Studio (auto cursor zoom, polished)
   - or OBS (max control)
3. **Audio**: load `pulse-2026-05-21-cto-norm.mp3` in your recorder OR play it in QuickTime/VLC alongside. If your tool can't mix, screen-record silent, then mix audio in iMovie/DaVinci.
4. **Click the CTO persona button BEFORE you start recording** so the dashboard is in CTO state from frame 0.
5. **Mute the in-app `<audio>` player** in the dashboard — you'll add the mp3 in post.

---

## Timeline — what to do at each timestamp

> Audio script is in `docs/submission/cto-narration.srt`. Burn that into the video as captions.

### 0:00 → 0:05  ·  greeting
- Static on **dashboard / (CTO persona already selected)**. Top of page visible: persona switcher, "Delivered at 7:55 AM · 3-min brief" header.

### 0:05 → 0:20  ·  headline (payment + checkout SLA)
- Slow **scroll down ~250px** so the headline quote / revenue+uptime cards come into frame.
- Pause there. Let the script set up the two problems.

### 0:20 → 0:53  ·  payment processing story (Story #1)
- **Scroll** to the first story card (payment processing failure).
- At ~0:30 (when narrator says "$11,748 direct revenue loss"), **hover over the dollar amount** so the citation tooltip pops.
- At ~0:45 (when narrator says "cause remains open"), scroll an extra ~100px so the cause / SPL citation chip is centered.

### 0:53 → 1:27  ·  checkout SLA story (Story #2)
- **Scroll** to the second story card (checkout SLA violation).
- At ~1:05 (narrator: "$1,500 credit liability"), pause cursor on that figure.
- At ~1:20 (narrator: "enterprise contract renewals become a harder conversation"), gentle scroll to next card.

### 1:27 → 1:55  ·  risk picture — 34 enterprise accounts, $816K
- **Scroll** so the risk-picture story (or the third story card) is centered.
- This is the punch line of the brief — **hold the frame**.

### 1:55 → 2:17  ·  decisions
- **Scroll down** to the "⚡ Decisions Required" section.
- At ~2:05, **click the first DecisionCard** (or hover over the "approve / hold release" buttons) so judges see one-click actions.

### 2:17 → 2:27  ·  good news + close
- **Scroll down to the "🎉 Good News" callout** (green/splunk-colored box near the bottom).
- Hold.

### 2:27 → 2:32  ·  audio ends — show drill-down
- **Scroll up to the "🔎 Ask about last night" drill-down section** (it sits above Good News).
- Visible but no click yet.

---

## Post-audio tour (2:32 → 2:50, silent or music bed)

The audio ends here. The next ~18 seconds are a silent flash-tour of the other two pages so judges see the breadth of Splunk-capability integration. Add subtle music bed or leave silent + burn in a label like "Plus: SPL Copilot · SOC Triage".

### 2:32 → 2:36  ·  drill-down click
- Back on dashboard `/`, in the drill-down panel: **click "Show me last night's payment errors"** suggestion chip.
- The Splunk-yellow SPL block appears. **Hold 2s on the SPL output** (it shows the "Splunk AI Assistant for SPL · conf 0.9" badge).

### 2:36 → 2:43  ·  SPL Copilot
- **Navigate to `/spl-copilot`**.
- Show the NL→SPL self-critique loop UI. **Scroll once** to reveal the output area.

### 2:43 → 2:50  ·  SOC Triage
- **Navigate to `/soc-triage`**.
- Show the autonomous investigation page. **Scroll once** through the findings / narrative.

### 2:50 → end  ·  outro card (optional)
- Title card: "Splunk Executive Pulse" + repo URL + tagline "From data to decisions, in 3 minutes".

---

## Tips that materially improve the take

1. **Browser zoom 100%**, not 90/110. Default Splunk-dark theme already in CSS.
2. **Disable mouse acceleration** for smooth cursor — System Settings → Mouse → Tracking speed slow.
3. **Hide your dock + menu bar** (System Settings → Desktop & Dock → "Automatically hide…").
4. **Close all other tabs** in the browser window. One tab, address bar empty or showing only the path (no tracking params).
5. **Don't show DevTools** (judges deduct).
6. **Burn-in captions** from `cto-narration.srt` — judges often watch muted.
7. **One clean take ≥ ten edited takes.** If you fluff a scroll, redo the whole thing. Editing seams under audio is brittle.
8. **Export 1080p MP4 (H.264, 60fps), ~30 Mbps.** Upload to YouTube (unlisted) or Vimeo (public).

---

## Files you need

| Asset | Path |
|-------|------|
| Audio | `web/public/audio/pulse-2026-05-21-cto-norm.mp3` |
| SRT captions | `docs/submission/cto-narration.srt` |
| Cover image | `web/public/audio/pulse-2026-05-21-cto-norm.png` (use as title card) |
| Title-card HTML (other personas) | `docs/submission/video_assets/title_cards.html` |
| Architecture diagram (judge requirement) | `ARCHITECTURE.md` (already in repo root) |

---

## Quick sanity test before final take

Open the URL, click CTO persona, scroll the page top-to-bottom in ~30 seconds. If every section renders, you're good. If a story card or the drill-down panel is missing, the API isn't returning data — restart Next.js (`PORT=3333 npm run dev` in `web/`) and retry.
