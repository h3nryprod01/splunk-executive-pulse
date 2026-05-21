# agents/narrative_writer/prompts/retry_prompt.py

RETRY_PROMPT_TEMPLATE = """\
Your previous draft has issues that MUST be fixed:

UNCITED NUMBERS (these numbers appear in the script but are not in the citations table — remove them or replace with qualitative language):
{uncited_list}

CRITIC FEEDBACK:
{critic_feedback}

Re-write the script. Same structure, same persona, same length budget.
Do NOT add new numbers. Do NOT remove correctly-cited information.

For any uncited claim, replace with qualitative phrasing:
  "$47K loss"  →  "a meaningful revenue impact"
  "2.3% drop"  →  "a small but persistent decline"
  "1,247 customers"  →  "over a thousand customers"

Return JSON in the same schema as before.
"""
