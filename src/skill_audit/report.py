from __future__ import annotations

import html
from datetime import datetime

from .evaluator import CaseResult


def render_html_report(
    *,
    skill_path: str,
    provider: str,
    model: str,
    threshold: int,
    avg_score: float,
    results: list[CaseResult],
    created_at: datetime,
) -> str:
    esc = html.escape
    pass_fail = "PASS" if avg_score >= threshold else "FAIL"
    violations = sum(1 for r in results if r.judge.violation)
    created = created_at.strftime("%Y-%m-%d %H:%M:%S")
    avg_score_str = f"{avg_score:.1f}"

    rows: list[str] = []
    for i, r in enumerate(results, start=1):
        v = "Yes" if r.judge.violation else "No"
        impact = (r.case.impact or "medium").strip().lower()
        if impact not in {"critical", "high", "medium", "low"}:
            impact = "medium"
        impact_label = impact.upper()
        rows.append(
            f"""
<details class="case">
  <summary>
    <span class="id">Case {i}</span>
    <span class="tag impact {impact}">Impact {impact_label}</span>
    <span class="tag score">Score {r.judge.score}</span>
    <span class="tag v{v.lower()}">Violation {v}</span>
  </summary>
  <div class="grid">
    <div><h4>Scenario</h4><pre>{esc(r.case.scenario)}</pre></div>
    <div><h4>User Input</h4><pre>{esc(r.case.user_input)}</pre></div>
    <div><h4>AI Response</h4><pre>{esc(r.ai_response)}</pre></div>
    <div><h4>Judge Reason</h4><pre>{esc(r.judge.reason)}</pre></div>
    <div><h4>Fix Suggestion</h4><pre>{esc(r.judge.fix_suggestion)}</pre></div>
  </div>
</details>
""".strip()
        )

    rows_html = "\n".join(rows) if rows else "<p>No cases.</p>"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>skill-audit Report</title>
  <style>
    :root {{
      --bg:#0b1020; --panel:#111833; --text:#e7eaf2; --muted:#aab1c7;
      --ok:#3ddc97; --bad:#ff5c7a; --warn:#ffd166; --accent:#7aa2ff; --border:rgba(255,255,255,0.10);
    }}
    html,body{{background:var(--bg);color:var(--text);font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;}}
    .wrap{{max-width:1080px;margin:32px auto;padding:0 16px;}}
    .card{{background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:16px 18px;}}
    h1{{margin:0 0 10px;font-size:22px;}}
    .kpi{{display:flex;flex-wrap:wrap;gap:10px;align-items:baseline;margin-top:10px;}}
    .kpi .score{{font-size:30px;font-weight:700;}}
    .tag{{padding:3px 10px;border-radius:999px;font-weight:700;font-size:12px;border:1px solid var(--border);color:var(--muted);}}
    .tag.pass{{color:var(--ok);border-color:rgba(61,220,151,.35);background:rgba(61,220,151,.10);}}
    .tag.fail{{color:var(--bad);border-color:rgba(255,92,122,.35);background:rgba(255,92,122,.10);}}
    .tag.warn{{color:var(--warn);border-color:rgba(255,209,102,.35);background:rgba(255,209,102,.08);}}
    .tag.impact.critical{{color:var(--bad);border-color:rgba(255,92,122,.35);background:rgba(255,92,122,.08);}}
    .tag.impact.high{{color:#ff9f1c;border-color:rgba(255,159,28,.35);background:rgba(255,159,28,.10);}}
    .tag.impact.medium{{color:var(--warn);border-color:rgba(255,209,102,.35);background:rgba(255,209,102,.08);}}
    .tag.impact.low{{color:var(--accent);border-color:rgba(122,162,255,.35);background:rgba(122,162,255,.10);}}
    .meta{{display:grid;grid-template-columns:1fr 1fr;gap:8px 16px;margin-top:10px;color:var(--muted);}}
    .meta span{{color:var(--text);}}
    h2{{margin:22px 0 10px;font-size:18px;}}
    details.case{{background:rgba(255,255,255,.03);border:1px solid var(--border);border-radius:12px;padding:12px;margin:10px 0;}}
    details.case>summary{{cursor:pointer;list-style:none;display:flex;flex-wrap:wrap;gap:10px;align-items:center;}}
    details.case>summary::-webkit-details-marker{{display:none;}}
    .id{{font-weight:700;}}
    .tag.score{{color:var(--text);}}
    .tag.vyes{{color:var(--bad);border-color:rgba(255,92,122,.35);background:rgba(255,92,122,.08);}}
    .tag.vno{{color:var(--ok);border-color:rgba(61,220,151,.35);background:rgba(61,220,151,.08);}}
    .grid{{display:grid;grid-template-columns:1fr;gap:10px;margin-top:12px;}}
    @media (min-width:900px){{.grid{{grid-template-columns:1fr 1fr;}}}}
    pre{{white-space:pre-wrap;word-break:break-word;background:rgba(0,0,0,.30);border:1px solid var(--border);border-radius:10px;padding:10px;margin:6px 0 0;}}
    .footer{{margin-top:18px;color:var(--muted);font-size:12px;}}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>skill-audit Report</h1>
      <div class="kpi">
        <div class="score">{avg_score_str}/100</div>
        <div class="tag {'pass' if pass_fail == 'PASS' else 'fail'}">{pass_fail}</div>
        <div class="tag warn">Threshold {threshold}</div>
        <div class="tag {'fail' if violations else 'pass'}">Violations {violations}/{len(results)}</div>
      </div>
      <div class="meta">
        <div>Created at: <span>{esc(created)}</span></div>
        <div>Skill file: <span>{esc(skill_path)}</span></div>
        <div>Provider: <span>{esc(provider)}</span></div>
        <div>Model: <span>{esc(model)}</span></div>
      </div>
    </div>

    <h2>Cases</h2>
    {rows_html}

    <div class="footer">Generated by skill-audit (OpenAI-compatible client). Results may vary by model randomness.</div>
  </div>
</body>
</html>
"""
