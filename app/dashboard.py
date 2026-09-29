from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .logging_config import LOG_PATH


def _percentile(arr: list[float | int], q: float) -> float:
    if not arr:
        return 0.0
    sorted_arr = sorted(arr)
    k = (len(sorted_arr) - 1) * (q / 100.0)
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_arr) else f
    return round(sorted_arr[f] + (sorted_arr[c] - sorted_arr[f]) * (k - f), 2)


def compute_dashboard_metrics() -> dict[str, Any]:
    if not LOG_PATH.exists():
        records = []
    else:
        records = []
        for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    requests = [r for r in records if r.get("event") == "request_received"]
    responses = [r for r in records if r.get("event") == "response_sent"]
    failures = [r for r in records if r.get("event") == "request_failed"]

    latencies = [r["latency_ms"] for r in responses if "latency_ms" in r]
    ttfts = [r["ttft_ms"] for r in responses if "ttft_ms" in r]

    p50 = _percentile(latencies, 50)
    p95 = _percentile(latencies, 95)
    p99 = _percentile(latencies, 99)
    ttft_p95 = _percentile(ttfts, 95)

    total_requests = len(requests)
    error_count = len(failures)
    error_rate = round((error_count / total_requests * 100) if total_requests else 0.0, 2)

    tool_successes = [r.get("tool_success") for r in responses if "tool_success" in r]
    tool_rate = round(
        (sum(1 for t in tool_successes if t is True) / len(tool_successes) * 100)
        if tool_successes
        else 100.0,
        2,
    )

    total_cost = round(sum(r.get("cost_usd", 0.0) for r in responses), 6)
    tokens_in = sum(r.get("tokens_in", 0) for r in responses)
    tokens_out = sum(r.get("tokens_out", 0) for r in responses)

    quality_scores = [r["quality_score"] for r in responses if "quality_score" in r]
    avg_quality = round(sum(quality_scores) / len(quality_scores), 3) if quality_scores else 0.0

    return {
        "latency": {
            "p50": p50,
            "p95": p95,
            "p99": p99,
            "ttft_p95": ttft_p95,
            "threshold": 3000,
            "status": "PASS" if p95 <= 3000 else "ALERT",
            "samples": latencies[-30:],
        },
        "traffic": {
            "total": total_requests,
            "rpm": total_requests,
            "threshold": 1,
            "status": "PASS" if total_requests >= 1 else "LOW",
        },
        "errors": {
            "error_rate_pct": error_rate,
            "error_count": error_count,
            "retrieval_success_pct": tool_rate,
            "threshold": 2.0,
            "status": "PASS" if error_rate <= 2.0 and tool_rate >= 90 else "ALERT",
        },
        "cost": {
            "total_usd": total_cost,
            "threshold": 2.5,
            "status": "PASS" if total_cost <= 2.5 else "ALERT",
        },
        "tokens": {
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "total": tokens_in + tokens_out,
            "threshold": 50000,
            "status": "PASS" if (tokens_in + tokens_out) <= 50000 else "ALERT",
        },
        "quality": {
            "mean": avg_quality,
            "threshold": 0.75,
            "status": "PASS" if avg_quality >= 0.75 else "ALERT",
        },
    }


def render_dashboard_html() -> str:
    m = compute_dashboard_metrics()
    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="30">
    <title>K4-L3A Day 13 Monitoring & LLMOps Dashboard</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: #0f172a;
            color: #f1f5f9;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            padding: 24px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #334155;
            padding-bottom: 16px;
            margin-bottom: 24px;
        }}
        .header h1 {{ font-size: 22px; color: #38bdf8; }}
        .meta-badges {{ display: flex; gap: 12px; }}
        .badge {{
            background: #1e293b;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 13px;
            border: 1px solid #475569;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
        }}
        .card {{
            background: #1e293b;
            border-radius: 10px;
            padding: 20px;
            border: 1px solid #334155;
            position: relative;
        }}
        .card h2 {{
            font-size: 15px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #94a3b8;
            margin-bottom: 12px;
        }}
        .metric-main {{
            font-size: 32px;
            font-weight: 700;
            color: #f8fafc;
            margin-bottom: 8px;
        }}
        .metric-sub {{
            font-size: 13px;
            color: #cbd5e1;
            line-height: 1.6;
        }}
        .status-badge {{
            position: absolute;
            top: 20px;
            right: 20px;
            font-size: 11px;
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 4px;
        }}
        .status-pass {{ background: #065f46; color: #34d399; }}
        .status-alert {{ background: #991b1b; color: #f87171; }}
        .threshold-label {{
            font-size: 12px;
            color: #64748b;
            margin-top: 10px;
            border-top: 1px solid #334155;
            padding-top: 8px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>K4-L3A Day 13 Monitoring & LLMOps Dashboard</h1>
            <div style="font-size: 13px; color: #64748b; margin-top: 4px;">Source: data/logs.jsonl | Auto-refresh: 30s</div>
        </div>
        <div class="meta-badges">
            <span class="badge">⏱ Time Range: Last 60m</span>
            <span class="badge">🔄 Refresh: 30s</span>
            <span class="badge">🎯 Target SLO: 99.5%</span>
        </div>
    </div>

    <div class="grid">
        <!-- Panel 1: Latency -->
        <div class="card">
            <span class="status-badge {'status-pass' if m['latency']['status'] == 'PASS' else 'status-alert'}">{m['latency']['status']}</span>
            <h2>1. Latency & TTFT</h2>
            <div class="metric-main">{m['latency']['p95']} <span style="font-size: 16px; color: #94a3b8;">ms (P95)</span></div>
            <div class="metric-sub">
                <div>• P50: <b>{m['latency']['p50']} ms</b> | P99: <b>{m['latency']['p99']} ms</b></div>
                <div>• TTFT P95: <b>{m['latency']['ttft_p95']} ms</b></div>
            </div>
            <div class="threshold-label">Threshold: P95 &le; {m['latency']['threshold']} ms (SLO)</div>
        </div>

        <!-- Panel 2: Traffic -->
        <div class="card">
            <span class="status-badge {'status-pass' if m['traffic']['status'] == 'PASS' else 'status-alert'}">{m['traffic']['status']}</span>
            <h2>2. Request Traffic</h2>
            <div class="metric-main">{m['traffic']['rpm']} <span style="font-size: 16px; color: #94a3b8;">req/min</span></div>
            <div class="metric-sub">
                <div>• Total requests: <b>{m['traffic']['total']}</b></div>
                <div>• Window: <b>60 minutes</b></div>
            </div>
            <div class="threshold-label">Threshold: rate &ge; {m['traffic']['threshold']} req/min</div>
        </div>

        <!-- Panel 3: Errors -->
        <div class="card">
            <span class="status-badge {'status-pass' if m['errors']['status'] == 'PASS' else 'status-alert'}">{m['errors']['status']}</span>
            <h2>3. Errors & Retrieval</h2>
            <div class="metric-main">{m['errors']['error_rate_pct']}% <span style="font-size: 16px; color: #94a3b8;">error rate</span></div>
            <div class="metric-sub">
                <div>• Failed requests: <b>{m['errors']['error_count']}</b></div>
                <div>• Retrieval Success: <b>{m['errors']['retrieval_success_pct']}%</b></div>
            </div>
            <div class="threshold-label">Threshold: error rate &le; {m['errors']['threshold']}%</div>
        </div>

        <!-- Panel 4: Cost -->
        <div class="card">
            <span class="status-badge {'status-pass' if m['cost']['status'] == 'PASS' else 'status-alert'}">{m['cost']['status']}</span>
            <h2>4. Cost Over Time</h2>
            <div class="metric-main">${m['cost']['total_usd']:.4f} <span style="font-size: 16px; color: #94a3b8;">USD</span></div>
            <div class="metric-sub">
                <div>• Pricing: $3/M in, $15/M out</div>
                <div>• Hourly accumulation</div>
            </div>
            <div class="threshold-label">Threshold: total &le; ${m['cost']['threshold']} USD</div>
        </div>

        <!-- Panel 5: Tokens -->
        <div class="card">
            <span class="status-badge {'status-pass' if m['tokens']['status'] == 'PASS' else 'status-alert'}">{m['tokens']['status']}</span>
            <h2>5. Token Consumption</h2>
            <div class="metric-main">{m['tokens']['total']} <span style="font-size: 16px; color: #94a3b8;">tokens</span></div>
            <div class="metric-sub">
                <div>• In: <b>{m['tokens']['tokens_in']}</b> tokens</div>
                <div>• Out: <b>{m['tokens']['tokens_out']}</b> tokens</div>
            </div>
            <div class="threshold-label">Threshold: total &le; {m['tokens']['threshold']} tokens</div>
        </div>

        <!-- Panel 6: Quality -->
        <div class="card">
            <span class="status-badge {'status-pass' if m['quality']['status'] == 'PASS' else 'status-alert'}">{m['quality']['status']}</span>
            <h2>6. Quality Proxy</h2>
            <div class="metric-main">{m['quality']['mean']} <span style="font-size: 16px; color: #94a3b8;">/ 1.0</span></div>
            <div class="metric-sub">
                <div>• Range: 0.0 &ndash; 1.0</div>
                <div>• Heuristic doc overlap & length</div>
            </div>
            <div class="threshold-label">Threshold: mean &ge; {m['quality']['threshold']}</div>
        </div>
    </div>
</body>
</html>
"""
