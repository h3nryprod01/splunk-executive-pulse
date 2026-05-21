# delivery/email.py
"""
Email delivery via Resend (https://resend.com).
Free tier: 100 emails/day, 3K emails/month — plenty for demo + early customers.
"""
from __future__ import annotations
import os
import logging
from pathlib import Path
from typing import Optional

import resend

from orchestration.state import PipelineState

logger = logging.getLogger(__name__)

PERSONA_EMAIL = {
    "CEO":  os.getenv("DEMO_CEO_EMAIL",  "ceo@demo.local"),
    "CFO":  os.getenv("DEMO_CFO_EMAIL",  "cfo@demo.local"),
    "CISO": os.getenv("DEMO_CISO_EMAIL", "ciso@demo.local"),
    "CTO":  os.getenv("DEMO_CTO_EMAIL",  "cto@demo.local"),
    "COO":  os.getenv("DEMO_COO_EMAIL",  "coo@demo.local"),
}

TEMPLATE_DIR = Path(__file__).parent / "templates"


async def deliver_email(state: PipelineState) -> bool:
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        logger.warning("RESEND_API_KEY missing — skipping email")
        return False

    persona = state["persona"].value
    script = state["narrative_script"]
    audio  = state["audio_output"]
    editor = state["editor_output"]

    resend.api_key = api_key

    html = _render_html_template(state)
    text = _render_text_template(state)
    date_str = state["briefing_date"].strftime("%A, %B %d")

    params = {
        "from":    os.getenv("PULSE_FROM_EMAIL", "Splunk Executive Pulse <pulse@demo.local>"),
        "to":      [PERSONA_EMAIL.get(persona, PERSONA_EMAIL["CEO"])],
        "subject": f"Your Executive Pulse · {date_str}",
        "html":    html,
        "text":    text,
        "tags":    [
            {"name": "persona", "value": persona},
            {"name": "run_id",  "value": state["run_id"]},
        ],
    }

    # Attach audio if file size < 10MB (Resend limit)
    audio_path = Path(audio.local_path)
    if audio_path.exists() and audio_path.stat().st_size < 10 * 1024 * 1024:
        with open(audio_path, "rb") as f:
            import base64
            params["attachments"] = [{
                "filename": audio_path.name,
                "content":  base64.b64encode(f.read()).decode("ascii"),
            }]

    try:
        resp = resend.Emails.send(params)
        logger.info(f"Email delivered to {persona}: id={resp.get('id')}")
        return True
    except Exception as e:
        logger.exception(f"Email delivery failed: {e}")
        raise


def _render_html_template(state: PipelineState) -> str:
    persona = state["persona"].value
    script  = state["narrative_script"]
    audio   = state["audio_output"]
    editor  = state["editor_output"]
    date_str = state["briefing_date"].strftime("%A, %B %d, %Y")

    # Stories HTML
    stories_html = ""
    for i, cluster in enumerate(editor.clusters, 1):
        theme_icon = _theme_icon(cluster.theme.value)
        stories_html += f"""
        <tr><td style="padding:16px 0; border-bottom:1px solid #334155;">
          <div style="font-size:11px; color:#94a3b8; letter-spacing:0.1em; text-transform:uppercase; margin-bottom:4px;">
            Story {i} · {cluster.theme.value.replace('_', ' ')}
          </div>
          <div style="font-size:16px; font-weight:600; color:#f1f5f9; line-height:1.4;">
            {theme_icon} {cluster.headline_hint}
          </div>
          {f'<div style="margin-top:8px; color:#f5b800; font-family:monospace; font-size:13px;">Exposure: ${cluster.aggregate_exposure_usd:,.0f}</div>' if cluster.aggregate_exposure_usd > 0 else ''}
        </td></tr>
        """

    # Decisions HTML
    decisions_html = ""
    for d in editor.decisions_required:
        cost_str = f"${d.cost_usd / 1000:.0f}K" if d.cost_usd else "—"
        decisions_html += f"""
        <tr><td style="padding:12px; background:#fff4d6; border-radius:8px;">
          <div style="font-size:11px; color:#1a1f36; opacity:0.6; text-transform:uppercase;">Decision · Owner: {d.owner}</div>
          <div style="font-weight:700; color:#1a1f36; margin-top:4px;">{d.title}</div>
          <div style="color:#1a1f36; font-size:14px; margin-top:6px;">{d.context_one_liner}</div>
          <div style="color:#1a1f36; font-family:monospace; font-size:12px; margin-top:8px;">
            {cost_str} · deadline: {d.deadline.strftime('%b %d') if d.deadline else 'TBD'}
          </div>
        </td></tr><tr><td style="height:8px;"></td></tr>
        """

    return f"""<!DOCTYPE html>
<html><body style="margin:0; background:#0a0e1a; color:#f1f5f9; font-family:-apple-system,BlinkMacSystemFont,'Inter',sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0e1a; padding:32px 16px;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" style="background:#1a1f36; border-radius:16px; overflow:hidden;">

      <!-- HEADER -->
      <tr><td style="padding:32px 32px 16px;">
        <div style="font-size:11px; color:#65a637; letter-spacing:0.2em; text-transform:uppercase;">Splunk Executive Pulse</div>
        <div style="font-size:24px; font-weight:800; margin-top:8px;">{date_str}</div>
        <div style="font-size:12px; color:#94a3b8; margin-top:4px;">Persona: <strong style="color:#f5b800;">{persona}</strong></div>
      </td></tr>

      <!-- AUDIO CTA -->
      <tr><td style="padding:8px 32px 24px;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:#1e293b; border:1px solid #334155; border-radius:12px;">
          <tr><td style="padding:20px;">
            <div style="font-size:11px; color:#94a3b8; text-transform:uppercase; letter-spacing:0.1em;">🎙️ Audio briefing · {audio.duration_sec}s</div>
            <div style="margin-top:8px;">
              <a href="{audio.audio_url}" style="display:inline-block; background:#65a637; color:#0a0e1a; padding:12px 24px; border-radius:999px; text-decoration:none; font-weight:700;">▶ Play</a>
            </div>
          </td></tr>
        </table>
      </td></tr>

      <!-- HEADLINE QUOTE -->
      <tr><td style="padding:0 32px 24px;">
        <div style="font-size:16px; font-style:italic; color:#cbd5e1; line-height:1.6; border-left:3px solid #65a637; padding-left:16px;">
          {_extract_intro(script.script_text)}
        </div>
      </td></tr>

      <!-- STORIES -->
      <tr><td style="padding:0 32px 24px;">
        <div style="font-size:11px; color:#94a3b8; text-transform:uppercase; letter-spacing:0.15em; margin-bottom:8px;">📰 Today's Stories</div>
        <table width="100%" cellpadding="0" cellspacing="0">{stories_html}</table>
      </td></tr>

      {f'''<!-- DECISIONS -->
      <tr><td style="padding:0 32px 24px;">
        <div style="font-size:11px; color:#94a3b8; text-transform:uppercase; letter-spacing:0.15em; margin-bottom:8px;">⚡ Decisions Required</div>
        <table width="100%" cellpadding="0" cellspacing="0">{decisions_html}</table>
      </td></tr>''' if decisions_html else ''}

      <!-- FOOTER -->
      <tr><td style="padding:24px 32px; border-top:1px solid #334155;">
        <div style="font-size:12px; color:#64748b;">
          Full details and drill-downs: <a href="{state.get('delivered_dashboard_url') or os.getenv('DASHBOARD_BASE_URL', 'http://localhost:3000')}" style="color:#65a637;">your dashboard →</a>
        </div>
        <div style="font-size:11px; color:#64748b; margin-top:8px;">
          Have a productive day. · run {state['run_id']}
        </div>
      </td></tr>

    </table>
  </td></tr>
</table>
</body></html>"""


def _render_text_template(state: PipelineState) -> str:
    script = state["narrative_script"]
    return f"""\
SPLUNK EXECUTIVE PULSE — {state['briefing_date'].strftime('%A, %B %d, %Y')}

Persona: {state['persona'].value}
Audio:   {state['audio_output'].audio_url} ({state['audio_output'].duration_sec}s)

────────────────────────────────────────

{script.script_text}

────────────────────────────────────────

Full details: {state.get('delivered_dashboard_url') or 'http://localhost:3000'}
Run: {state['run_id']}
"""


def _theme_icon(theme: str) -> str:
    return {
        "revenue_incident":          "💰",
        "security_threat":           "🛡️",
        "performance_degradation":   "📉",
        "cost_overrun":              "💸",
        "deploy_incident":           "🚀",
        "capacity_risk":             "📊",
        "compliance_risk":           "⚖️",
        "positive_milestone":        "🎉",
    }.get(theme, "📌")


def _extract_intro(script_text: str) -> str:
    """Pull the first 2 sentences for email preview."""
    sentences = script_text.split(". ")
    return ". ".join(sentences[:2]).rstrip(".") + "."
