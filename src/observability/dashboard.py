"""Bonus B1: Observability dashboard (static HTML, khong can server) sinh tu artifacts cua pipeline.

Hien thi: trang thai Quality Gate + Freshness cua 3 trang thai, metric RAG, phan bo tuoi bai bao
(drift ve freshness), cac loi da tiem va lich su self-healing. Mo file `data/reports/dashboard.html`.
"""
from __future__ import annotations

from html import escape
import json
import math
from pathlib import Path
from typing import Any

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_text

STATES = ("baseline", "corrupted", "repaired")
STATE_LABELS = {"baseline": "Baseline", "corrupted": "Corrupted", "repaired": "Repaired"}
RAG_METRICS = (
    ("retrieval_hit_rate", "Hit rate"),
    ("mean_token_f1", "Token F1"),
    ("judge_accuracy", "Judge accuracy"),
)
AGE_BIN_DAYS = 30


def _load(path: Path) -> Any:
    return read_json(path) if path.exists() else None


def collect_dashboard_data(settings: Settings) -> dict[str, Any]:
    """Doc artifacts cua pipeline thanh mot dict duy nhat (cung duoc nhung vao HTML de xem/tai lai)."""
    paths = settings.paths
    frames = {"baseline": paths.clean_json, "corrupted": paths.corrupted_clean_json, "repaired": paths.repaired_clean_json}
    metrics = {"baseline": paths.baseline_metrics, "corrupted": paths.corrupted_metrics, "repaired": paths.repaired_metrics}
    quality = {
        "baseline": paths.baseline_quality_report,
        "corrupted": paths.corrupted_quality_report,
        "repaired": paths.quality_dir / "repaired_quality_report.json",
    }
    states: dict[str, Any] = {}
    for state in STATES:
        rows = _load(frames[state]) or []
        states[state] = {
            "available": bool(rows),
            "ages": [int(row["age_days"]) for row in rows if row.get("age_days") is not None],
            "metrics": _load(metrics[state]),
            "quality": _load(quality[state]),
        }
    corruption_log = _load(paths.corruption_log) or {}
    return {
        "generated_at": now_utc().isoformat(timespec="seconds"),
        "threshold_days": settings.freshness_threshold_days,
        "states": states,
        "corruption_counts": corruption_log.get("corruption_counts", {}),
        "self_healing": _load(paths.self_healing_log) or [],
    }


# ---------------------------------------------------------------- rendering helpers

def _pct(value: Any) -> str:
    return "–" if value is None else f"{float(value):.1%}"


def _num(value: Any, digits: int = 3) -> str:
    return "–" if value is None else f"{float(value):.{digits}f}"


def _status(ok: bool | None, good: str = "PASS", bad: str = "FAIL") -> str:
    if ok is None:
        return '<span class="status status-na">– N/A</span>'
    if ok:
        return f'<span class="status status-good"><span aria-hidden="true">✓</span> {good}</span>'
    return f'<span class="status status-critical"><span aria-hidden="true">✕</span> {bad}</span>'


def _tile(label: str, value: str, sub: str = "") -> str:
    return (f'<div class="tile"><div class="tile-label">{escape(label)}</div>'
            f'<div class="tile-value">{value}</div><div class="tile-sub">{sub}</div></div>')


def _table(headers: list[str], rows: list[list[str]], caption: str) -> str:
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return (f'<details class="table-view"><summary>Table view: {escape(caption)}</summary>'
            f'<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></details>')


def _legend(items: list[tuple[str, str]]) -> str:
    keys = "".join(
        f'<span class="legend-item"><svg width="12" height="12" aria-hidden="true">'
        f'<rect width="12" height="12" rx="3" fill="var({var})"/></svg>{escape(label)}</span>'
        for var, label in items
    )
    return f'<div class="legend">{keys}</div>'


def _bar_path(x: float, y: float, w: float, h: float, r: float = 4.0) -> str:
    """Bar voi 2 goc tren bo tron (data-end), day phang tai baseline."""
    r = min(r, w / 2, h)
    return (f"M{x:.1f},{y + h:.1f} V{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} "
            f"H{x + w - r:.1f} Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} V{y + h:.1f} Z")


def _rag_chart(data: dict[str, Any]) -> str:
    width, height, left, bottom, top = 640, 260, 44, 32, 16
    plot_h = height - bottom - top
    group_w = (width - left - 16) / len(RAG_METRICS)
    bar_w, gap = 26, 2
    parts = [f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="RAG metrics by state">']
    for tick in (0, 0.25, 0.5, 0.75, 1.0):
        y = top + plot_h * (1 - tick)
        parts.append(f'<line class="grid" x1="{left}" x2="{width - 8}" y1="{y:.1f}" y2="{y:.1f}"/>'
                     f'<text class="axis" x="{left - 8}" y="{y + 4:.1f}" text-anchor="end">{tick:.2f}</text>')
    rows = []
    for g, (key, label) in enumerate(RAG_METRICS):
        cx = left + group_w * g + group_w / 2
        start = cx - (len(STATES) * bar_w + (len(STATES) - 1) * gap) / 2
        row = [escape(label)]
        for s, state in enumerate(STATES):
            value = (data["states"][state]["metrics"] or {}).get(key)
            row.append(_num(value))
            if value is None:
                continue
            h = max(plot_h * float(value), 1)
            x = start + s * (bar_w + gap)
            tip = f"{STATE_LABELS[state]} · {label}: {float(value):.3f}"
            parts.append(f'<path class="mark" d="{_bar_path(x, top + plot_h - h, bar_w, h)}" '
                         f'fill="var(--series-{s + 1})" tabindex="0" data-tip="{escape(tip)}"/>')
            if state == "corrupted":  # direct label chon loc: gia tri bi suy giam
                parts.append(f'<text class="value" x="{x + bar_w / 2:.1f}" y="{top + plot_h - h - 6:.1f}" '
                             f'text-anchor="middle">{float(value):.2f}</text>')
        parts.append(f'<text class="axis" x="{cx:.1f}" y="{height - 10}" text-anchor="middle">{escape(label)}</text>')
        rows.append(row)
    parts.append(f'<line class="baseline" x1="{left}" x2="{width - 8}" y1="{top + plot_h}" y2="{top + plot_h}"/></svg>')
    legend = _legend([(f"--series-{i + 1}", STATE_LABELS[s]) for i, s in enumerate(STATES)])
    table = _table(["Metric", *(STATE_LABELS[s] for s in STATES)], rows, "RAG metrics")
    return legend + "".join(parts) + table


def _age_histograms(data: dict[str, Any]) -> str:
    threshold = data["threshold_days"]
    all_ages = [age for state in STATES for age in data["states"][state]["ages"]]
    if not all_ages:
        return '<p class="muted">No clean data found — run the pipelines first.</p>'
    max_age = max(max(all_ages), threshold + AGE_BIN_DAYS)
    n_bins = math.ceil((max_age + 1) / AGE_BIN_DAYS)
    counts = {
        state: [sum(1 for a in data["states"][state]["ages"] if b * AGE_BIN_DAYS <= a < (b + 1) * AGE_BIN_DAYS)
                for b in range(n_bins)]
        for state in STATES
    }
    y_max = max(1, max(max(c) for c in counts.values()))
    width, height, left, bottom, top = 300, 170, 28, 30, 14
    plot_w, plot_h = width - left - 8, height - bottom - top
    bin_w = plot_w / n_bins
    panels, rows = [], []
    for state in STATES:
        ages = data["states"][state]["ages"]
        stale = sum(1 for a in ages if a > threshold)
        parts = [f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="{STATE_LABELS[state]} age distribution">']
        for tick in range(0, y_max + 1, max(1, math.ceil(y_max / 4))):
            y = top + plot_h * (1 - tick / y_max)
            parts.append(f'<line class="grid" x1="{left}" x2="{width - 8}" y1="{y:.1f}" y2="{y:.1f}"/>'
                         f'<text class="axis" x="{left - 6}" y="{y + 4:.1f}" text-anchor="end">{tick}</text>')
        for b, count in enumerate(counts[state]):
            if not count:
                continue
            h = plot_h * count / y_max
            x = left + b * bin_w + 1
            tip = f"{STATE_LABELS[state]} · {b * AGE_BIN_DAYS}–{(b + 1) * AGE_BIN_DAYS - 1} days: {count} papers"
            parts.append(f'<path class="mark" d="{_bar_path(x, top + plot_h - h, bin_w - 2, h, 3)}" '
                         f'fill="var(--series-1)" tabindex="0" data-tip="{escape(tip)}"/>')
        tx = left + plot_w * threshold / (n_bins * AGE_BIN_DAYS)
        parts.append(f'<line class="threshold" x1="{tx:.1f}" x2="{tx:.1f}" y1="{top - 4}" y2="{top + plot_h}"/>'
                     f'<text class="axis" x="{tx + 4:.1f}" y="{top + 6}">{threshold}d SLA</text>'
                     f'<line class="baseline" x1="{left}" x2="{width - 8}" y1="{top + plot_h}" y2="{top + plot_h}"/>'
                     f'<text class="axis" x="{left}" y="{height - 10}">0</text>'
                     f'<text class="axis" x="{width - 8}" y="{height - 10}" text-anchor="end">{n_bins * AGE_BIN_DAYS} days</text></svg>')
        ratio = stale / len(ages) if ages else None
        panels.append(f'<figure class="panel"><figcaption><strong>{STATE_LABELS[state]}</strong>'
                      f'<span class="muted"> · stale {stale}/{len(ages)} ({_pct(ratio)})</span></figcaption>'
                      + "".join(parts) + "</figure>")
        rows.append([STATE_LABELS[state], str(len(ages)), str(stale), _pct(ratio),
                     str(min(ages)) if ages else "–", str(max(ages)) if ages else "–"])
    table = _table(["State", "Papers", f"Stale (> {threshold}d)", "Stale ratio", "Min age", "Max age"], rows,
                   "paper age distribution")
    return f'<div class="multiples">{"".join(panels)}</div>{table}'


def _quality_matrix(data: dict[str, Any]) -> str:
    keys: list[tuple[str, str | None]] = []
    for state in STATES:
        for check in (data["states"][state]["quality"] or {}).get("checks", []):
            key = (check["expectation"], check.get("column"))
            if key not in keys:
                keys.append(key)
    head = "".join(f"<th>{STATE_LABELS[s]}</th>" for s in STATES)
    rows = []
    for expectation, column in keys:
        cells = []
        for state in STATES:
            check = next((c for c in (data["states"][state]["quality"] or {}).get("checks", [])
                          if (c["expectation"], c.get("column")) == (expectation, column)), None)
            if check is None:
                cells.append(_status(None))
                continue
            detail = check.get("unexpected_count")
            detail = check.get("observed_value") if detail is None else detail
            extra = f' <span class="muted">({escape(str(detail))})</span>' if detail not in (None, 0) else ""
            cells.append(_status(bool(check["success"])) + extra)
        rows.append(f'<tr><td><code>{escape(expectation)}</code> <span class="muted">{escape(column or "table")}</span></td>'
                    + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    fresh = []
    for state in STATES:
        freshness = (data["states"][state]["quality"] or {}).get("freshness") or {}
        ok = freshness.get("is_fresh")
        fresh.append(_status(ok, "FRESH", "STALE") + f' <span class="muted">({_pct(freshness.get("stale_ratio"))})</span>')
    rows.append("<tr><td><strong>Freshness SLA</strong> <span class=\"muted\">≤ 25% stale</span></td>"
                + "".join(f"<td>{c}</td>" for c in fresh) + "</tr>")
    return f'<div class="scroll"><table><thead><tr><th>Check</th>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def _corruption_chart(data: dict[str, Any]) -> str:
    counts = data["corruption_counts"]
    if not counts:
        return '<p class="muted">No corruption log yet.</p>'
    width, row_h, left = 640, 30, 170
    height = row_h * len(counts) + 8
    c_max = max(counts.values())
    parts = [f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="Injected corruption events">']
    for i, (kind, count) in enumerate(counts.items()):
        y = 4 + i * row_h
        w = max((width - left - 40) * count / c_max, 2)
        tip = f"{kind}: {count} events"
        parts.append(f'<text class="axis label" x="{left - 10}" y="{y + 17}" text-anchor="end">{escape(kind)}</text>'
                     f'<rect class="mark" x="{left}" y="{y + 4}" width="{w:.1f}" height="{row_h - 10}" rx="4" '
                     f'fill="var(--series-1)" tabindex="0" data-tip="{escape(tip)}"/>'
                     f'<text class="value" x="{left + w + 6:.1f}" y="{y + 17}">{count}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _healing_table(data: dict[str, Any]) -> str:
    incidents = data["self_healing"]
    if not incidents:
        return '<p class="muted">No self-healing incidents recorded.</p>'
    rows = []
    for incident in reversed(incidents[-10:]):
        detected = incident.get("detected") or {}
        failed = ", ".join(detected.get("failed_expectations") or []) or "–"
        if detected.get("is_fresh") is False:
            failed += " + freshness"
        rows.append(
            f"<tr><td>{escape(str(incident.get('detected_at', ''))[:19].replace('T', ' '))}</td>"
            f"<td>{escape(str(incident.get('stage')))}</td><td>{escape(failed)}</td>"
            f"<td><code>{escape(str(incident.get('action')))}</code></td>"
            f"<td>{_status(incident.get('resolved'), 'RESOLVED', 'BLOCKED')}</td></tr>"
        )
    return ("<div class=\"scroll\"><table><thead><tr><th>Detected (UTC)</th><th>Stage</th><th>Gate failures</th>"
            f"<th>Auto action</th><th>Outcome</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>")


CSS = """
:root{color-scheme:light;--page:#f9f9f7;--surface-1:#fcfcfb;--text-primary:#0b0b0b;--text-secondary:#52514e;
--muted:#898781;--grid:#e1e0d9;--axis:#c3c2b7;--border:rgba(11,11,11,.10);--series-1:#2a78d6;--series-2:#eb6834;
--series-3:#1baf7a;--good:#006300;--critical:#d03b3b}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--page:#0d0d0d;--surface-1:#1a1a19;
--text-primary:#fff;--text-secondary:#c3c2b7;--grid:#2c2c2a;--axis:#383835;--border:rgba(255,255,255,.10);
--series-1:#3987e5;--series-2:#d95926;--series-3:#199e70;--good:#0ca30c;--critical:#e66767}}
:root[data-theme="dark"]{color-scheme:dark;--page:#0d0d0d;--surface-1:#1a1a19;--text-primary:#fff;--text-secondary:#c3c2b7;
--grid:#2c2c2a;--axis:#383835;--border:rgba(255,255,255,.10);--series-1:#3987e5;--series-2:#d95926;--series-3:#199e70;
--good:#0ca30c;--critical:#e66767}
*{box-sizing:border-box}body{margin:0;background:var(--page);color:var(--text-primary);
font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1080px;margin:0 auto;padding:24px 16px 48px}h1{font-size:22px;margin:0 0 4px}
h2{font-size:16px;margin:0 0 12px}.muted{color:var(--muted)}.sub{color:var(--text-secondary);margin:0 0 20px}
.card{background:var(--surface-1);border:1px solid var(--border);border-radius:12px;padding:16px 20px;margin-bottom:16px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-bottom:16px}
.tile{background:var(--surface-1);border:1px solid var(--border);border-radius:12px;padding:14px 16px}
.tile-label{color:var(--text-secondary);font-size:13px}.tile-value{font-size:20px;font-weight:600;margin:4px 0}
.tile-sub{color:var(--muted);font-size:12px}.status{font-weight:600;white-space:nowrap}
.status-good{color:var(--good)}.status-critical{color:var(--critical)}.status-na{color:var(--muted)}
svg{max-width:100%;height:auto;display:block;overflow:visible}.grid{stroke:var(--grid);stroke-width:1}
.baseline{stroke:var(--axis);stroke-width:1}.threshold{stroke:var(--text-secondary);stroke-width:1.5}
.axis{fill:var(--muted);font-size:11px;font-variant-numeric:tabular-nums}.axis.label{fill:var(--text-secondary);font-size:12px}
.value{fill:var(--text-primary);font-size:11px;font-weight:600}.mark{cursor:default;outline:none}
.mark:hover,.mark:focus{filter:brightness(1.15)}
.legend{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:8px;color:var(--text-secondary);font-size:13px}
.legend-item{display:inline-flex;align-items:center;gap:6px}
.multiples{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
.panel{margin:0}.panel figcaption{font-size:13px;margin-bottom:4px}
table{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--grid)}th{color:var(--text-secondary);font-weight:600}
.scroll{overflow-x:auto}.table-view{margin-top:10px}.table-view summary{cursor:pointer;color:var(--text-secondary)}
code{font-size:12px}#tip{position:fixed;pointer-events:none;background:var(--surface-1);color:var(--text-primary);
border:1px solid var(--border);border-radius:8px;padding:6px 10px;font-size:12px;box-shadow:0 4px 16px rgba(0,0,0,.12);
display:none;z-index:10}
"""

JS = """
const tip=document.getElementById('tip');
function show(el,x,y){tip.textContent=el.dataset.tip;tip.style.display='block';
tip.style.left=Math.min(x+12,innerWidth-tip.offsetWidth-8)+'px';tip.style.top=(y+12)+'px';}
document.querySelectorAll('[data-tip]').forEach(el=>{
el.addEventListener('pointermove',e=>show(el,e.clientX,e.clientY));
el.addEventListener('pointerleave',()=>tip.style.display='none');
el.addEventListener('focus',()=>{const r=el.getBoundingClientRect();show(el,r.right,r.top);});
el.addEventListener('blur',()=>tip.style.display='none');});
"""


def render_dashboard(data: dict[str, Any]) -> str:
    states = data["states"]
    tiles = []
    for state in STATES:
        quality = states[state]["quality"] or {}
        freshness = quality.get("freshness") or {}
        failed = len(quality.get("failed_expectations") or [])
        sub = (f"{quality.get('row_count', '–')} rows · {failed} failed checks · "
               f"stale {_pct(freshness.get('stale_ratio'))}") if quality else "not run yet"
        tiles.append(_tile(f"{STATE_LABELS[state]} quality gate", _status(quality.get("success") if quality else None), sub))
    healed = [i for i in data["self_healing"] if i.get("resolved")]
    tiles.append(_tile("Self-healing", f"{len(healed)} auto-repaired",
                       f"{len(data['self_healing'])} incidents logged"))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Data Observability Dashboard</title><style>{CSS}</style></head>
<body><main>
<h1>Data Observability Dashboard</h1>
<p class="sub">Crossref → RAG pipeline · Baseline vs Corrupted vs Repaired · generated {escape(data['generated_at'])} UTC</p>
<div class="tiles">{''.join(tiles)}</div>
<section class="card"><h2>Quality gate (Great Expectations 1.x) &amp; freshness SLA</h2>{_quality_matrix(data)}</section>
<section class="card"><h2>RAG performance by state</h2>{_rag_chart(data)}</section>
<section class="card"><h2>Paper age distribution — freshness drift ({AGE_BIN_DAYS}-day bins)</h2>{_age_histograms(data)}</section>
<section class="card"><h2>Injected corruptions (events)</h2>{_corruption_chart(data)}</section>
<section class="card"><h2>Self-healing incidents</h2>{_healing_table(data)}</section>
</main><div id="tip" role="tooltip"></div>
<script type="application/json" id="dashboard-data">{escape(json.dumps(data, ensure_ascii=True))}</script>
<script>{JS}</script></body></html>
"""


def build_dashboard(settings: Settings, output_path: Path | None = None) -> Path:
    path = output_path or settings.paths.dashboard_html
    write_text(path, render_dashboard(collect_dashboard_data(settings)))
    return path


def main() -> None:
    print(build_dashboard(load_settings()))
