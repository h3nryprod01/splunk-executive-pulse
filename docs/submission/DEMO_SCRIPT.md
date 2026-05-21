# Demo video script — Splunk Executive Pulse (target 2:58)

Judges often watch muted — burn in captions. The 60-second audio in Scene 3 must be
your **real generated TTS output**, not a human read. That is the wow.

## Scene 1 — The problem (0:00–0:20)
- **0:00–0:05** Cold open: clock at 7:55 AM, coffee, hand reaches for phone.
- **0:05–0:12** CEO opens laptop in a car; Slack shows "247 unread"; a wall of Splunk
  graphs/SPL appears. CEO (frustrated): *"What actually happened last night? Just tell
  me what I need to know."*
- **0:12–0:20** Title card: *"Enterprises spend $4B/year on observability. The people
  making million-dollar decisions can't read the output."*

## Scene 2 — The solution (0:20–0:40)
- Logo + tagline: *"From operational data to executive decisions. In three minutes."*
- Narrator: *"Executive Pulse reads your Splunk data overnight, translates technical
  signals into business stories, and delivers a personalized briefing — by email,
  audio, and dashboard."*

## Scene 3 — The demo (0:40–2:15)  ★ hero
- **0:40–0:50** Phone shows email 7:55 AM: *"Your Executive Pulse — Tuesday May 21"*.
- **0:50–1:50 — PLAY 60s OF REAL TTS** over a waveform; dashboard auto-scrolls to each
  story as named:

  > *"Good morning. This is your Splunk Executive Pulse for Tuesday, May 21st. Overall,
  > a positive night — online revenue hit 2.3 million dollars, four percent above
  > forecast, 99.94 percent uptime. But one story needs your attention. At 2:47 AM our
  > payment gateway failed for twelve minutes. We estimate forty-seven thousand dollars
  > in lost revenue and twelve hundred customers affected — including 34 enterprise
  > accounts. Root cause: a deployment that bypassed our staging gate. Second story: we
  > blocked our third credential-stuffing attack this month. No accounts compromised,
  > but the trend is up forty percent. Your CISO is requesting two hundred forty
  > thousand dollars for multi-factor authentication. Full details are in your
  > dashboard. Have a productive day."*

- **1:50–2:00 — Personalization reveal.** Same data, switch persona: CFO brief leads
  with cost; **CISO brief leads with the attack.** Narrator: *"Same data. Different
  lens."*
- **2:00–2:15 — Payoff.** 8:30 AM exec meeting; CEO walks in: *"Tell me about the
  payment incident — what's our enterprise recovery plan?"* CTO looks impressed.

## Scene 4 — How it works (2:15–2:40)
- Animated architecture; components light up. Narrator: *"Executive Pulse uses the
  Splunk MCP Server to query data, Splunk Hosted Models for narration, and a
  multi-agent pipeline that enriches every signal with business context."*
- Highlight the Business Context Layer. *"Every number is traceable. Every claim cites
  its source. No hallucinations."*

## Scene 5 — Close (2:40–2:58)
- Three stats: *"3 minutes vs. 2-hour briefing prep" / "engineers → C-suite" / "every
  Splunk customer has a CEO."* Narrator: *"Splunk already powers the world's data. Now
  it powers the world's decisions."* Logo + repo URL.

## Recording checklist
- [ ] Generate the real 60s TTS (ElevenLabs "Adam"/"Bill", 1.0x) — `audio_producer`.
- [ ] Screen-record the dashboard persona switch (`cd web && npm run dev`).
- [ ] Show a terminal run of `python orchestration/graph_e2e_demo.py` (the pipeline).
- [ ] Burn-in captions; subtle piano bed; Splunk dark + gold palette.
- [ ] Keep total ≤ 3:00. Export 1080p MP4. Upload to YouTube/Vimeo (public/unlisted).
