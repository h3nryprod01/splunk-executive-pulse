#!/usr/bin/env bash
# run_demo.sh
# Splunk Executive Pulse — full demo runner.
#
# What it does (designed for screen recording):
#   1. Boots the stack
#   2. Generates and seeds synthetic data
#   3. Runs pipeline for CEO persona (visible in terminal)
#   4. Switches to CFO persona to show personalization
#   5. Opens the dashboard
#   6. Plays the resulting audio
#
# Designed to be:
#   - Idempotent (safe to re-run)
#   - Visible (lots of echo)
#   - Pausable (PAUSE markers for screen-record cuts)

set -euo pipefail

# ============================================================
# Pretty output
# ============================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
GOLD='\033[0;33m'
SPLUNK_GREEN='\033[38;5;112m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

step() {
    echo ""
    echo -e "${SPLUNK_GREEN}${BOLD}▶ $1${NC}"
    echo -e "${DIM}$(date '+%H:%M:%S')${NC}"
}
ok()    { echo -e "  ${GREEN}✓${NC} $1"; }
warn()  { echo -e "  ${GOLD}⚠${NC} $1"; }
fail()  { echo -e "  ${RED}✗${NC} $1"; exit 1; }
pause() {
    if [[ "${INTERACTIVE:-1}" == "1" ]]; then
        echo -e "${DIM}── press Enter to continue ──${NC}"
        read -r
    fi
}

# ============================================================
# Pre-flight
# ============================================================
clear
cat <<'EOF'
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║       SPLUNK EXECUTIVE PULSE — DEMO RUNNER                 ║
║       From data to decisions, in 3 minutes.                ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
EOF

step "Pre-flight checks"
command -v docker >/dev/null || fail "docker not installed"
command -v python3 >/dev/null || fail "python3 not installed"
command -v ffmpeg >/dev/null || warn "ffmpeg not installed — audio post-processing will be skipped"
[ -f .env ] || fail ".env missing — run: cp .env.example .env"
source .env
[ -n "${ELEVENLABS_API_KEY:-}" ] || warn "ELEVENLABS_API_KEY missing — TTS will fail"
[ -n "${ANTHROPIC_API_KEY:-}" ] || warn "ANTHROPIC_API_KEY missing — LLM will fall back"
ok "All checks passed"

pause

# ============================================================
# Stack
# ============================================================
step "1/6 · Boot the stack (Splunk + Postgres + Redis + MCP + Pipeline)"
docker compose up -d
echo -e "${DIM}Waiting for Splunk health (~60s on first run)...${NC}"
until docker compose ps splunk 2>/dev/null | grep -q "healthy"; do
    printf "."
    sleep 5
done
echo ""
ok "Stack healthy"
ok "Splunk Web:    http://localhost:8000   (admin / changeme123!)"
ok "Postgres:      localhost:5432   (pulse / pulse_dev)"
ok "MCP Server:    http://localhost:9000"

pause

# ============================================================
# Synthetic data
# ============================================================
step "2/6 · Generate synthetic data (the demo night, 350K events, 5 stories)"
python3 splunk_data/generate_full_dataset.py
ok "Dataset generated in splunk_data/samples/"

step "3/6 · Seed business context + push events to Splunk"
python3 -m business_context.loader
ok "Business context loaded: services, customers, SLAs, budgets"
python3 splunk_data/push_to_splunk_hec.py
ok "Events streamed into Splunk via HEC"

pause

# ============================================================
# Pipeline — CEO
# ============================================================
step "4/6 · Run pipeline for CEO persona ${BOLD}(this is the moment)${NC}"
echo -e "${DIM}You'll see each of the 7 agents fire in sequence.${NC}\n"
docker compose exec -T pipeline python -m orchestration.runner CEO 2>&1 | \
    grep --line-buffered -E "span\.(start|end)|pipeline\.(start|done)|metric" | \
    while read -r line; do
        if echo "$line" | grep -q "span.start"; then
            stage=$(echo "$line" | grep -oP '"span": "\K[^"]+')
            echo -e "  ${SPLUNK_GREEN}→${NC} $stage..."
        elif echo "$line" | grep -q "span.end"; then
            stage=$(echo "$line" | grep -oP '"span": "\K[^"]+')
            ms=$(echo "$line" | grep -oP '"duration_ms": \K\d+')
            status=$(echo "$line" | grep -oP '"status": "\K[^"]+')
            if [ "$status" == "ok" ]; then
                echo -e "  ${GREEN}✓${NC} $stage done (${ms}ms)"
            else
                echo -e "  ${RED}✗${NC} $stage failed (${ms}ms)"
            fi
        fi
    done
ok "CEO briefing generated"

# Find the latest mp3
CEO_AUDIO=$(ls -t demo/sample_outputs/pulse-*-ceo*.mp3 2>/dev/null | head -1 || true)
[ -n "$CEO_AUDIO" ] || fail "no CEO audio file produced"
ok "Audio: $CEO_AUDIO"

pause

# ============================================================
# Personalization — CFO + CISO
# ============================================================
step "5/6 · Demonstrate personalization — same data, different lens"
echo -e "${DIM}Running CFO + CISO in parallel...${NC}\n"
docker compose exec -T pipeline python -c "
import asyncio
from agents.executive_editor.models import Persona
from orchestration.runner import run_briefing

async def main():
    await asyncio.gather(
        run_briefing(Persona.CFO),
        run_briefing(Persona.CISO),
    )

asyncio.run(main())
" 2>&1 | grep --line-buffered -E "node\.(executive_editor|audio_producer)\.done" | head -20

ok "CFO and CISO briefings generated"
ls -1 demo/sample_outputs/pulse-*.mp3 | tail -3 | while read -r f; do
    ok "  $f"
done

pause

# ============================================================
# Showcase
# ============================================================
step "6/6 · Open the dashboard + play the audio"

if command -v open >/dev/null; then
    open "http://localhost:3000" 2>/dev/null || true
elif command -v xdg-open >/dev/null; then
    xdg-open "http://localhost:3000" 2>/dev/null || true
fi
ok "Dashboard opened at http://localhost:3000"

echo ""
echo -e "${GOLD}🎙️  Playing CEO briefing...${NC}"
if command -v afplay >/dev/null; then
    afplay "$CEO_AUDIO"
elif command -v mpg123 >/dev/null; then
    mpg123 "$CEO_AUDIO"
elif command -v ffplay >/dev/null; then
    ffplay -nodisp -autoexit "$CEO_AUDIO" 2>/dev/null
fi

# ============================================================
# Wrap
# ============================================================
echo ""
echo -e "${SPLUNK_GREEN}${BOLD}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${SPLUNK_GREEN}${BOLD}║                                                            ║${NC}"
echo -e "${SPLUNK_GREEN}${BOLD}║       ✓ Demo complete                                      ║${NC}"
echo -e "${SPLUNK_GREEN}${BOLD}║                                                            ║${NC}"
echo -e "${SPLUNK_GREEN}${BOLD}║       Dashboard:    http://localhost:3000                  ║${NC}"
echo -e "${SPLUNK_GREEN}${BOLD}║       Splunk Web:   http://localhost:8000                  ║${NC}"
echo -e "${SPLUNK_GREEN}${BOLD}║       Audio files:  demo/sample_outputs/                   ║${NC}"
echo -e "${SPLUNK_GREEN}${BOLD}║                                                            ║${NC}"
echo -e "${SPLUNK_GREEN}${BOLD}║       To stop:      make down                              ║${NC}"
echo -e "${SPLUNK_GREEN}${BOLD}║                                                            ║${NC}"
echo -e "${SPLUNK_GREEN}${BOLD}╚════════════════════════════════════════════════════════════╝${NC}"
