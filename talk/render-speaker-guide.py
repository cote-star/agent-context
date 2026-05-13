#!/usr/bin/env python3
"""Render slide-narratives.md into a print-friendly speaker guide HTML."""

from __future__ import annotations

import html
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "slide-narratives.md"
OUT = ROOT / "speaker-guide.html"


def inline_md(text: str) -> str:
    placeholders: list[str] = []

    def code_repl(match: re.Match[str]) -> str:
        placeholders.append(f"<code>{html.escape(match.group(1))}</code>")
        return f"\u0000{len(placeholders) - 1}\u0000"

    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", code_repl, escaped)
    escaped = re.sub(r"\*\*([^*]+):\*\*", r"<strong>\1:</strong>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)

    def restore(match: re.Match[str]) -> str:
        return placeholders[int(match.group(1))]

    return re.sub(r"\u0000(\d+)\u0000", restore, escaped)


def paragraph(lines: list[str]) -> str:
    text = " ".join(line.strip() for line in lines).strip()
    return f"<p>{inline_md(text)}</p>" if text else ""


def render_blocks(raw: str) -> str:
    lines = raw.strip().splitlines()
    out: list[str] = []
    para: list[str] = []
    quote: list[str] = []

    def flush_para() -> None:
        nonlocal para
        if para:
            out.append(paragraph(para))
            para = []

    def flush_quote() -> None:
        nonlocal quote
        if quote:
            body = "\n".join(f"<p>{inline_md(q)}</p>" for q in quote if q.strip())
            out.append(f'<blockquote>{body}</blockquote>')
            quote = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_para()
            flush_quote()
            continue

        point = re.match(r"^\*\*Point:\*\*\s*(.*)$", stripped)
        talk = re.match(r"^\*\*Talk track:\*\*\s*$", stripped)
        transition = re.match(r"^\*\*Transition:\*\*\s*$", stripped)
        final_line = re.match(r"^\*\*Final line:\*\*\s*$", stripped)

        if point:
            flush_para()
            flush_quote()
            out.append(
                '<div class="cue cue-point"><div class="cue-label">Point</div>'
                f'<div class="cue-text">{inline_md(point.group(1))}</div></div>'
            )
            continue
        if talk:
            flush_para()
            flush_quote()
            out.append('<h3>Talk Track</h3>')
            continue
        if transition:
            flush_para()
            flush_quote()
            out.append('<h3 class="transition-label">Transition</h3>')
            continue
        if final_line:
            flush_para()
            flush_quote()
            out.append('<h3 class="final-label">Final Line</h3>')
            continue
        if stripped.startswith(">"):
            flush_para()
            quote.append(stripped[1:].strip())
            continue

        flush_quote()
        para.append(stripped)

    flush_para()
    flush_quote()
    return "\n".join(out)


def main() -> None:
    source = SOURCE.read_text()
    title_match = re.match(r"^#\s+(.+)$", source, re.M)
    doc_title = title_match.group(1) if title_match else "Slide Narratives"
    parts = re.split(r"^## Slide\s+(\d{2})\s+-\s+(.+)$", source, flags=re.M)
    intro = parts[0]
    slides = []
    for i in range(1, len(parts), 3):
        slides.append((parts[i], parts[i + 1].strip(), parts[i + 2]))

    nav = "\n".join(
        f'<a class="nav-chip" href="#slide-{num}">{num}</a>' for num, _, _ in slides
    )
    cards = "\n".join(
        f"""
        <article class="note-card" id="slide-{num}">
          <header class="note-head">
            <div>
              <span class="eyebrow">Slide {num}</span>
              <h2>{html.escape(title)}</h2>
            </div>
            <a class="top-link" href="#top">Top</a>
          </header>
          <div class="note-body">
            {render_blocks(body)}
          </div>
        </article>
        """
        for num, title, body in slides
    )

    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>{html.escape(doc_title)} · Agent-Context Speaker Guide</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet" />
<style>
:root {{
  --bg: #0A0E1A;
  --bg-soft: #0E1422;
  --surface: #131826;
  --surface-2: #1A2030;
  --border: #2A3142;
  --border-soft: #1F2533;
  --fg: #F8FAFC;
  --fg-mid: #D1D5DB;
  --fg-dim: #94A3B8;
  --fg-faint: #64748B;
  --green: #10B981;
  --green-soft: rgba(16,185,129,.13);
  --green-line: rgba(16,185,129,.42);
  --orange: #F97316;
  --orange-soft: rgba(249,115,22,.13);
  --orange-line: rgba(249,115,22,.45);
  --radius: 14px;
  --radius-sm: 8px;
  --mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  --sans: 'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
}}
* {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{
  margin: 0;
  background:
    radial-gradient(1100px 600px at 80% -10%, rgba(16,185,129,.05), transparent 60%),
    radial-gradient(900px 500px at -5% 110%, rgba(249,115,22,.05), transparent 60%),
    var(--bg);
  color: var(--fg);
  font-family: var(--sans);
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}}
a {{ color: var(--green); text-decoration: none; border-bottom: 1px solid var(--green-line); }}
code, .mono {{ font-family: var(--mono); font-feature-settings: 'liga' 0; }}
.page {{ width: min(1080px, calc(100% - 40px)); margin: 0 auto; padding: 42px 0 72px; }}
.hero {{
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: linear-gradient(180deg, #10162A 0%, #0A0E1A 100%);
  padding: 34px 38px;
  box-shadow: 0 24px 80px rgba(0,0,0,.35);
}}
.kicker, .eyebrow {{
  display: block;
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: .14em;
  text-transform: uppercase;
  color: var(--green);
}}
h1, h2, h3 {{ margin: 0; letter-spacing: -0.015em; }}
h1 {{ margin-top: 10px; font-size: clamp(36px, 6vw, 62px); line-height: 1; }}
.subtitle {{ margin: 14px 0 0; max-width: 780px; color: var(--fg-mid); font-size: 18px; }}
.memory-grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 24px;
}}
.memory {{
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface);
  padding: 14px 16px;
}}
.memory b {{ color: var(--fg); }}
.memory p {{ margin: 4px 0 0; color: var(--fg-dim); font-size: 14px; }}
.nav {{
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
  margin: 18px 0 24px;
}}
.nav-chip {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 30px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--surface);
  color: var(--fg-mid);
  font: 600 12px/1 var(--mono);
}}
.note-card {{
  margin-top: 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: linear-gradient(180deg, rgba(255,255,255,.018), transparent 32%), var(--surface);
  overflow: hidden;
  page-break-inside: avoid;
}}
.note-head {{
  display: flex;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 22px 14px;
  border-bottom: 1px solid var(--border-soft);
}}
.note-head h2 {{ margin-top: 4px; font-size: 26px; line-height: 1.15; }}
.top-link {{ color: var(--fg-faint); font: 600 11px/1 var(--mono); letter-spacing: .12em; text-transform: uppercase; border-bottom: 0; }}
.note-body {{ padding: 18px 22px 22px; }}
.note-body h3 {{
  margin: 14px 0 8px;
  color: var(--green);
  font: 600 11px/1 var(--mono);
  letter-spacing: .14em;
  text-transform: uppercase;
}}
.note-body h3.transition-label {{ color: var(--orange); }}
.note-body h3.final-label {{ color: var(--fg); }}
p {{ margin: 0 0 10px; color: var(--fg-mid); font-size: 15.5px; }}
strong {{ color: var(--fg); font-weight: 650; }}
code {{
  background: var(--surface-2);
  color: var(--fg);
  border-radius: 5px;
  padding: .1em .38em;
  font-size: .9em;
}}
.cue {{
  display: grid;
  grid-template-columns: 86px 1fr;
  gap: 14px;
  align-items: start;
  margin-bottom: 14px;
  border-left: 2px solid var(--green);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  background: var(--green-soft);
  padding: 12px 14px;
}}
.cue-label {{
  color: var(--green);
  font: 600 10.5px/1.3 var(--mono);
  letter-spacing: .14em;
  text-transform: uppercase;
}}
.cue-text {{ color: var(--fg); font-size: 16.5px; }}
blockquote {{
  margin: 12px 0;
  padding: 12px 16px;
  border-left: 2px solid var(--orange);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  background: var(--orange-soft);
}}
blockquote p {{ color: var(--fg); margin: 0 0 8px; }}
blockquote p:last-child {{ margin-bottom: 0; }}
.footer-note {{
  margin-top: 24px;
  color: var(--fg-faint);
  font: 500 12px/1.5 var(--mono);
  text-align: center;
}}
@media (max-width: 720px) {{
  .page {{ width: min(100% - 24px, 1080px); padding-top: 20px; }}
  .hero {{ padding: 24px; }}
  .memory-grid {{ grid-template-columns: 1fr; }}
  .cue {{ grid-template-columns: 1fr; gap: 6px; }}
}}
@media print {{
  @page {{ size: A4; margin: 12mm; }}
  html {{ scroll-behavior: auto; }}
  body {{ background: var(--bg); -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  .page {{ width: 100%; padding: 0; }}
  .hero, .note-card {{ box-shadow: none; }}
  .nav, .top-link {{ display: none; }}
  .note-card {{ break-inside: avoid; margin-top: 10px; }}
  .note-head {{ padding: 14px 18px 10px; }}
  .note-body {{ padding: 14px 18px 16px; }}
  p {{ font-size: 12.5px; margin-bottom: 7px; }}
  .note-head h2 {{ font-size: 20px; }}
  .cue-text {{ font-size: 13.5px; }}
  h1 {{ font-size: 38px; }}
  .subtitle {{ font-size: 14px; }}
}}
</style>
</head>
<body id="top">
  <main class="page">
    <section class="hero">
      <span class="kicker">Agent-Context · Speaker Guide</span>
      <h1>Slide Narratives</h1>
      <p class="subtitle">A rehearsal-first companion to the Cursor Meetup deck. Use it to remember the point, land the concrete example, and move cleanly to the next slide.</p>
      <div class="memory-grid">
        <div class="memory"><b>1. State the point</b><p>One sentence. No apology. Let the slide support you.</p></div>
        <div class="memory"><b>2. Ground it</b><p>Use the concrete repo, human navigation, or test evidence example.</p></div>
        <div class="memory"><b>3. Move forward</b><p>Each transition tells the room why the next slide exists.</p></div>
      </div>
    </section>
    <nav class="nav" aria-label="Slide shortcuts">{nav}</nav>
    {cards}
    <p class="footer-note">Source: slide-narratives.md · Rendered for quick rehearsal and printable PDF.</p>
  </main>
</body>
</html>
"""
    OUT.write_text(document)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
