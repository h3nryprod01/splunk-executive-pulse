# orchestration/observability.py
"""
Structured logging + metrics emission.
In prod, replace _emit_metric with OTel/Prometheus/Datadog client.
"""
from __future__ import annotations
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

logger = logging.getLogger("pulse.orchestration")


def structured_log(event: str, **fields):
    """One-line JSON log entry — pipes cleanly into Splunk."""
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    logger.info(json.dumps(payload, default=str))


def _emit_metric(name: str, value: float, tags: dict):
    """Hook for metric backends. Default: log only."""
    structured_log("metric", metric_name=name, value=value, tags=tags)


@asynccontextmanager
async def span(name: str, **tags):
    """Async context manager to time a block."""
    start = time.perf_counter()
    structured_log("span.start", span=name, **tags)
    try:
        yield
        duration_ms = int((time.perf_counter() - start) * 1000)
        _emit_metric("pulse.span.duration_ms", duration_ms,
                     {"span": name, "status": "ok", **tags})
        structured_log("span.end", span=name, duration_ms=duration_ms, status="ok")
    except Exception as e:
        duration_ms = int((time.perf_counter() - start) * 1000)
        _emit_metric("pulse.span.duration_ms", duration_ms,
                     {"span": name, "status": "error", **tags})
        structured_log("span.end", span=name, duration_ms=duration_ms,
                       status="error", error=str(e), error_type=type(e).__name__)
        raise
