# delivery/slack.py
"""
Slack delivery via incoming webhooks (no app install needed for demo).
For production: use Slack Web API with bot token + interactive buttons.
"""
from __future__ import annotations
import os
import logging
import httpx

from orchestration.state import PipelineState

logger = logging.getLogger(__name__)


async def deliver_slack(state: PipelineState) -> bool:
    webhook = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook:
        logger.warning("SLACK_WEBHOOK_URL missing — skipping Slack")
        return False

    blocks = _build_blocks(state)

    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(webhook, json={"blocks": blocks})
        r.raise_for_status()

    logger.info(f"Slack delivered for {state['persona'].value}")
    return True


async def deliver_failure_alert(state: PipelineState) -> bool:
    """Best-effort alert when pipeline fails."""
    webhook = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook:
        return False

    errors = state.get("errors", [])
    persona = state["persona"].value
    err_lines = "\n".join([
        f"• `{e['node']}`: {e['error_type']} — {e['message'][:120]}"
        for e in errors[:5]
    ]) or "(no error details)"

    async with httpx.AsyncClient(timeout=15) as c:
        await c.post(webhook, json={
            "blocks": [
                {"type": "header", "text": {"type": "plain_text",
                    "text": f"⚠️ Executive Pulse failed · {persona}"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": err_lines}},
                {"type": "context", "elements": [{"type": "mrkdwn",
                    "text": f"run `{state['run_id']}` · stage `{state.get('current_stage','?')}`"}]},
            ]
        })
    return True


def _build_blocks(state: PipelineState) -> list[dict]:
    persona = state["persona"].value
    script = state["narrative_script"]
    audio  = state["audio_output"]
    editor = state["editor_output"]
    date_str = state["briefing_date"].strftime("%A, %b %d")

    blocks: list[dict] = [
        {"type": "header", "text": {"type": "plain_text",
            "text": f"🎙️ Executive Pulse · {persona} · {date_str}"}},
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"_{_first_two_sentences(script.script_text)}_"}},
        {"type": "actions", "elements": [
            {"type": "button",
             "text": {"type": "plain_text", "text": f"▶ Play audio ({audio.duration_sec}s)"},
             "url":  audio.audio_url,
             "style": "primary"},
            {"type": "button",
             "text": {"type": "plain_text", "text": "Open dashboard"},
             "url":  state.get("delivered_dashboard_url") or os.getenv("DASHBOARD_BASE_URL", "http://localhost:3000")},
        ]},
        {"type": "divider"},
    ]

    # Story summaries
    for i, c in enumerate(editor.clusters[:3], 1):
        icon = {"revenue_incident":"💰","security_threat":"🛡️","performance_degradation":"📉",
                "cost_overrun":"💸","deploy_incident":"🚀"}.get(c.theme.value, "📌")
        exposure_str = f" · *${c.aggregate_exposure_usd:,.0f}* exposure" if c.aggregate_exposure_usd > 0 else ""
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
            "text": f"{icon} *Story {i}:* {c.headline_hint}{exposure_str}"}})

    # Decisions
    if editor.decisions_required:
        blocks.append({"type": "divider"})
        for d in editor.decisions_required:
            cost_str = f" · ${d.cost_usd/1000:.0f}K" if d.cost_usd else ""
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn",
                    "text": f"⚡ *Decision needed:* {d.title}{cost_str}\n_{d.context_one_liner}_"},
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Review"},
                    "url": state.get("delivered_dashboard_url") or "http://localhost:3000",
                },
            })

    blocks.append({"type": "context", "elements": [
        {"type": "mrkdwn", "text": f"_run `{state['run_id']}` · {script.word_count} words · {script.llm_passes} pass(es)_"},
    ]})

    return blocks


def _first_two_sentences(text: str) -> str:
    parts = text.split(". ")
    return ". ".join(parts[:2]).rstrip(".") + "."
