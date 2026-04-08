"""HTML reporter for CAF audit results."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def status_badge(status: str) -> str:
    colors = {"PASS": "#22c55e", "FAIL": "#ef4444", "ERROR": "#f97316", "SKIP": "#94a3b8"}
    color = colors.get(status, "#94a3b8")
    return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600">{status}</span>'


def metric_card(label: str, value: str, sub: str = "") -> str:
    return f"""
    <div style="background:#1e293b;border-radius:8px;padding:16px;min-width:140px;text-align:center">
      <div style="color:#94a3b8;font-size:12px;margin-bottom:4px">{label}</div>
      <div style="color:#f1f5f9;font-size:28px;font-weight:700">{value}</div>
      {f'<div style="color:#64748b;font-size:11px">{sub}</div>' if sub else ''}
    </div>"""


def module_row(m: dict) -> str:
    status = m.get("status", "UNKNOWN")
    metrics = m.get("metrics", {})
    failures = m.get("failures", [])
    failure_html = ""
    if failures:
        items = "".join(f"<li><code>{f['test']}</code>: {f['reason']}</li>" for f in failures[:5])
        failure_html = f'<ul style="color:#fca5a5;font-size:12px;margin:4px 0 0 16px">{items}</ul>'

    return f"""
    <tr style="border-bottom:1px solid #1e293b">
      <td style="padding:12px 16px;font-weight:600;color:#e2e8f0">{m.get('module','?')}</td>
      <td style="padding:12px 16px">{status_badge(status)}</td>
      <td style="padding:12px 16px;text-align:right;color:#94a3b8">{m.get('tests_run',0)}</td>
      <td style="padding:12px 16px;text-align:right;color:#22c55e">{m.get('tests_passed',0)}</td>
      <td style="padding:12px 16px;text-align:right;color:#ef4444">{m.get('tests_failed',0)}</td>
      <td style="padding:12px 16px;text-align:right;color:#94a3b8">{m.get('duration_ms',0):.0f}ms</td>
      <td style="padding:12px 16px;color:#94a3b8;font-size:12px">
        {f"acc: {metrics['accuracy_pct']:.1f}%" if 'accuracy_pct' in metrics else ""}
        {f" · p99: {metrics['p99_latency_ms']:.1f}ms" if 'p99_latency_ms' in metrics else ""}
        {f" · rss: {metrics['memory_rss_mb']:.1f}MB" if 'memory_rss_mb' in metrics else ""}
        {failure_html}
      </td>
    </tr>"""


def render(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    modules = report.get("modules", [])
    overall = report.get("overall_status", "UNKNOWN")
    gen_at = report.get("generated_at", "")

    module_rows = "".join(module_row(m) for m in modules)
    pass_rate = summary.get("pass_rate_pct", 0)
    dur_s = summary.get("total_duration_ms", 0) / 1000

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CAF Audit Report</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0f172a; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 32px; }}
  h1 {{ font-size: 24px; font-weight: 700; margin-bottom: 4px; }}
  h2 {{ font-size: 16px; font-weight: 600; color: #94a3b8; margin: 24px 0 12px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ text-align: left; padding: 8px 16px; color: #64748b; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; background: #1e293b; }}
  tr:hover {{ background: rgba(255,255,255,0.02); }}
  code {{ background: #1e293b; padding: 1px 5px; border-radius: 3px; font-size: 11px; }}
</style>
</head>
<body>
  <div style="max-width:1100px;margin:0 auto">
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:24px">
      <h1>CAF Audit Report</h1>
      {status_badge(overall)}
    </div>
    <div style="color:#64748b;font-size:13px;margin-bottom:24px">Generated: {gen_at} · Framework: {report.get('framework','')}</div>

    <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:32px">
      {metric_card("Tests Run", str(summary.get('total_tests',0)))}
      {metric_card("Passed", str(summary.get('total_passed',0)), f"{pass_rate:.1f}%")}
      {metric_card("Failed", str(summary.get('total_failed',0)))}
      {metric_card("Duration", f"{dur_s:.1f}s")}
      {metric_card("Modules", str(len(modules)))}
    </div>

    <h2>Module Results</h2>
    <table>
      <thead>
        <tr>
          <th>Module</th><th>Status</th><th style="text-align:right">Tests</th>
          <th style="text-align:right">Pass</th><th style="text-align:right">Fail</th>
          <th style="text-align:right">Duration</th><th>Metrics / Failures</th>
        </tr>
      </thead>
      <tbody>{module_rows}</tbody>
    </table>

    <div style="margin-top:48px;color:#334155;font-size:12px;text-align:center">
      Claude Agentic Framework · Audit Suite v1.0
    </div>
  </div>
</body>
</html>"""


def save(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(report))
    print(f"HTML report saved: {path}")
