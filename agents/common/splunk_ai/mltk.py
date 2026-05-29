"""
Splunk AI Toolkit (MLTK / AITK) SPL builders.

Instead of hand-rolled sigma thresholds, detectors can run Splunk-native
anomaly detection and forecasting via MLTK SPL commands. These builders return
SPL strings that the Signal Collector executes through the MCP search tool.

MLTK reference commands:
  | anomalydetection   — distribution/IQR-based outlier flagging
  | fit / | apply      — train/score models (e.g. DensityFunction)
  | predict            — time-series forecasting with confidence bands
"""
from __future__ import annotations


def anomaly_detection_spl(
    index: str, sourcetype: str, by_field: str = "service",
    span: str = "1m", method: str = "anomalydetection",
) -> str:
    """
    Flag anomalous buckets for a metric stream.

    method="anomalydetection" uses MLTK's built-in command;
    method="density" trains a DensityFunction and scores outliers.
    """
    base = (
        f"search index={index} sourcetype={sourcetype} status>=500 "
        f"| bin _time span={span} "
        f"| stats count AS error_count by _time, {by_field}"
    )
    if method == "density":
        return (
            base
            + " | fit DensityFunction error_count by " + by_field
            + " into payment_density"
            + " | apply payment_density"
            + ' | where "IsOutlier(error_count)"=1'
        )
    return base + " | anomalydetection error_count action=annotate"


def count_anomaly_spl(
    index: str, sourcetype: str, where: str = "",
    by_field: str = "src_ip", span: str = "1m",
) -> str:
    """Flag anomalous event-count buckets for any filtered stream.

    Generic counterpart to anomaly_detection_spl (which is error-rate specific).
    Used e.g. for detecting a credential-stuffing burst on an auth source.
    """
    base = f"search index={index} sourcetype={sourcetype} {where}".strip()
    return (
        base
        + f" | bin _time span={span}"
        + f" | stats count AS event_count by _time, {by_field}"
        + " | anomalydetection event_count action=annotate"
    )


def forecast_spl(
    index: str, sourcetype: str, metric: str = "p99(response_ms)",
    span: str = "1h", future_timespan: int = 24, holdback: int = 0,
) -> str:
    """
    Forecast a latency/throughput metric with MLTK's predict, exposing the
    upper confidence band so a detector can flag breaches of expected behavior.
    """
    metric_alias = metric.replace("(", "_").replace(")", "")
    return (
        f"search index={index} sourcetype={sourcetype} "
        f"| timechart span={span} {metric} AS {metric_alias} "
        f"| predict {metric_alias} as forecast "
        f"future_timespan={future_timespan} holdback={holdback} "
        f"| eval breach=if({metric_alias} > upper95(forecast), 1, 0)"
    )
