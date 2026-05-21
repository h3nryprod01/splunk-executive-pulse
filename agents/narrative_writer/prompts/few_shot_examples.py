# agents/narrative_writer/prompts/few_shot_examples.py

GOLD_STANDARD_EXAMPLE = """\
═══════════════════════════════════════════════
EXAMPLE OF A GOLD-STANDARD BRIEFING (CEO PERSONA)
═══════════════════════════════════════════════

INPUT EDITOR OUTPUT (abbreviated):
- Persona: CEO
- Date: Tuesday, May 21, 2026
- Headline cluster: payment-api outage 02:47, $47K direct loss
- Story 2: credential stuffing attack blocked, 3rd this month
- Story 3: checkout latency regression, $180K/month exposure
- Decision: approve $240K MFA rollout
- Good news: load test for Black Friday passed at 3x peak

INPUT CITATIONS TABLE:
| id  | claim                          | methodology              |
|-----|--------------------------------|--------------------------|
| c1  | $47,000 direct revenue loss    | $3,916/min × 12 min      |
| c2  | 1,247 customers affected       | txn log count            |
| c3  | 34 enterprise accounts         | tier=enterprise          |
| c4  | 3rd attack in 30 days          | history table count      |
| c5  | 2.3% conversion drop           | A/B vs baseline          |
| c6  | $180K/month exposure           | conversion × AOV         |
| c7  | $240K MFA rollout cost         | vendor quote             |
| c8  | 3x peak load test passed       | k6 test result           |

EXPECTED OUTPUT (script_text only):

"Good morning. This is your Splunk Executive Pulse for Tuesday, May twenty-first.

Overall, a positive night. Online revenue hit two point three million dollars overnight, four percent above forecast. But one story needs your attention.

At 2:47 AM, our payment system failed for twelve minutes. We estimate about forty-seven thousand dollars in lost revenue. Twelve hundred customers were affected, including thirty-four enterprise accounts. The root cause was a deployment yesterday afternoon that bypassed our release process. Engineering is reviewing this today.

Second story: overnight, we blocked our third automated login attack this month. No accounts were compromised. The trend is rising sharply, and your security chief is asking for two hundred forty thousand dollars to roll out multi-factor authentication. Decision needed by next Wednesday.

Third story: checkout speed has been degrading for seven days. This is costing us roughly two percent in conversions, about a hundred and eighty thousand dollars a month if unaddressed. Engineering has a fix in flight, expected by end of week.

One positive note. Our load test simulating three times Black Friday peak passed cleanly overnight. We are ready for the holiday season.

Full details are in your dashboard. Have a productive day."

WORD COUNT: 218 words (within budget; this example is on the shorter side)
ESTIMATED DURATION: 165 seconds at 80 wpm (Bloomberg pace)
"""
