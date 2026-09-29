import json
from pathlib import Path

# 05: PII redaction
lines = [l for l in Path("data/logs.jsonl").read_text(encoding="utf-8").splitlines() if "[REDACTED_" in l]
out_pii = ["=== PII REDACTION EVIDENCE IN data/logs.jsonl ===\n"]
for i, line in enumerate(lines[:5], 1):
    rec = json.loads(line)
    out_pii.append(f"Sample {i} (Event: {rec.get('event')}, Correlation ID: {rec.get('correlation_id')}):")
    out_pii.append(json.dumps(rec, indent=2, ensure_ascii=False))
    out_pii.append("")
Path("submission/evidence/05-pii-redaction.txt").write_text("\n".join(out_pii), encoding="utf-8")
print("Saved 05-pii-redaction.txt")

# 13: Incident log
incident_ids = ["req-852ec6e8", "req-ab23406b", "req-54f7c474", "req-8f4d8344", "req-9250dc7a"]
out_inc = [
    "=== INCIDENT LOGS EVIDENCE (Challenge: day13-k4-l3a-monitoring-llmops-v1 | Scenario: rag_slow) ===\n",
    "Affected correlation IDs: " + ", ".join(incident_ids),
    "Affected feature: monitoring\n"
]
for line in Path("data/logs.jsonl").read_text(encoding="utf-8").splitlines():
    if any(cid in line for cid in incident_ids):
        rec = json.loads(line)
        out_inc.append(f"Event: {rec.get('event')} | ID: {rec.get('correlation_id')} | Latency: {rec.get('latency_ms')}ms")
        out_inc.append(json.dumps(rec, indent=2, ensure_ascii=False))
        out_inc.append("")
Path("submission/evidence/13-incident-log.txt").write_text("\n".join(out_inc), encoding="utf-8")
print("Saved 13-incident-log.txt")
