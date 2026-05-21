# agents/narrative_writer/llm_client.py
"""
LLM client with Splunk Hosted Models as primary, fallback to Anthropic/OpenAI.
"""
from __future__ import annotations
import os
import logging
import httpx
import json
from typing import Optional

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(
        self,
        primary_endpoint: str = None,
        primary_token: str = None,
        fallback: Optional[str] = None,  # "anthropic" | "openai" | None
    ):
        self.primary_endpoint = primary_endpoint or os.getenv("SPLUNK_LLM_ENDPOINT")
        self.primary_token = primary_token or os.getenv("SPLUNK_LLM_TOKEN")
        self.fallback = fallback or os.getenv("LLM_FALLBACK", "anthropic")
        self.last_model_used: str = ""

    async def complete_json(
        self, system: str, user: str,
        max_tokens: int = 2000, temperature: float = 0.3,
    ) -> dict:
        """Returns parsed JSON. Tries primary; on failure, fallback."""
        try:
            result = await self._call_splunk_hosted(system, user, max_tokens, temperature)
            self.last_model_used = "splunk-hosted"
            return result
        except Exception as e:
            logger.warning(f"Splunk hosted model failed: {e}; falling back to {self.fallback}")
            if self.fallback == "anthropic":
                result = await self._call_anthropic(system, user, max_tokens, temperature)
                self.last_model_used = "claude-sonnet"
                return result
            elif self.fallback == "openai":
                result = await self._call_openai(system, user, max_tokens, temperature)
                self.last_model_used = "gpt-4"
                return result
            raise

    async def _call_splunk_hosted(self, system, user, max_tokens, temperature):
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(
                f"{self.primary_endpoint}/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.primary_token}"},
                json={
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "response_format": {"type": "json_object"},
                },
            )
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            return json.loads(content)

    async def _call_anthropic(self, system, user, max_tokens, temperature):
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": os.getenv("ANTHROPIC_API_KEY"),
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-6",
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                },
            )
            r.raise_for_status()
            text = r.json()["content"][0]["text"]
            # Strip ```json fences if present
            text = text.strip()
            if text.startswith("```"):
                text = "\n".join(text.split("\n")[1:-1])
            return json.loads(text)

    async def _call_openai(self, system, user, max_tokens, temperature):
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "response_format": {"type": "json_object"},
                },
            )
            r.raise_for_status()
            return json.loads(r.json()["choices"][0]["message"]["content"])
