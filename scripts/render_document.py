#!/usr/bin/env python3
"""Build a printable, self-contained HTML manual without external packages."""
import html
import os
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def inline(text):
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', escaped)


def anchor(text):
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def render(markdown):
    lines = markdown.splitlines()
    output = []
    navigation = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.startswith("```"):
            language = line[3:]
            block = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                block.append(lines[index])
                index += 1
            if language == "mermaid":
                output.append('<figure>' + (ROOT / "docs/arquitectura.svg").read_text() + '</figure>')
            else:
                output.append("<pre><code>" + html.escape("\n".join(block)) + "</code></pre>")
            index += 1
            continue
        heading = re.match(r"^(#{1,3}) (.+)$", line)
        if heading:
            level, text = len(heading[1]), heading[2]
            identifier = anchor(text)
            output.append(f'<h{level} id="{identifier}">{inline(text)}</h{level}>')
            if level == 2:
                navigation.append(f'<a href="#{identifier}">{html.escape(text)}</a>')
            index += 1
            continue
        if line.startswith("|"):
            rows = []
            while index < len(lines) and lines[index].startswith("|"):
                cells = [cell.strip() for cell in lines[index].strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", cell) for cell in cells):
                    tag = "th" if not rows else "td"
                    rows.append("<tr>" + "".join(f"<{tag}>{inline(cell)}</{tag}>" for cell in cells) + "</tr>")
                index += 1
            output.append('<div class="table-wrap"><table><thead>' + rows[0] + "</thead><tbody>" + "".join(rows[1:]) + "</tbody></table></div>")
            continue
        if re.match(r"^\d+\. ", line):
            items = []
            while index < len(lines) and re.match(r"^\d+\. ", lines[index]):
                items.append("<li>" + inline(re.sub(r"^\d+\. ", "", lines[index])) + "</li>")
                index += 1
            output.append("<ol>" + "".join(items) + "</ol>")
            continue
        if line.startswith("- "):
            items = []
            while index < len(lines) and lines[index].startswith("- "):
                items.append("<li>" + inline(lines[index][2:]) + "</li>")
                index += 1
            output.append("<ul>" + "".join(items) + "</ul>")
            continue
        paragraph = []
        while index < len(lines) and lines[index].strip():
            paragraph.append(lines[index])
            index += 1
        output.append("<p>" + inline(" ".join(paragraph)) + "</p>")
    return "".join(output), "".join(navigation)


def main(destination=None):
    local_manual = destination is None
    body, navigation = render((ROOT / "docs/FUNCIONAMIENTO.md").read_text())
    template = '''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Funcionamiento de Goliat - Nexus</title>
<style>
:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#edf1f6;color:#1e293b;font:16px/1.65 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}main{max-width:1080px;margin:40px auto;padding:54px 68px 72px;background:#fff;border:1px solid #d9e2ed;border-radius:12px}h1,h2,h3{color:#000;line-height:1.22;scroll-margin-top:24px}h1{font-size:38px;font-weight:720;max-width:820px;letter-spacing:-1px;margin:8px 0 22px}h2{font-size:25px;margin:48px 0 18px}h3{font-size:19px;margin:30px 0 14px}p{margin:0 0 18px}a{color:#225b92;text-decoration-thickness:1px;text-underline-offset:3px}code{font:0.87em ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere}p code,td code{background:#f2f5f9;padding:2px 4px;border-radius:3px}pre{padding:20px 22px;background:#f4f7fb;border:1px solid #d9e2ed;border-radius:6px;overflow:auto;line-height:1.55;margin:24px 0;white-space:pre-wrap;overflow-wrap:anywhere}.table-wrap{overflow:auto;margin:24px 0}table{width:100%;border-collapse:collapse;table-layout:auto;font-size:14px;line-height:1.55}th,td{border:1px solid #d1dae5;padding:13px 15px;vertical-align:top;overflow-wrap:anywhere}th{text-align:left;background:#e8eff7;color:#000;font-weight:650}tbody tr:nth-child(even){background:#f8fafc}figure{margin:28px 0}svg{width:100%;height:auto}nav{display:flex;flex-wrap:wrap;gap:8px 18px;margin:0 0 35px;padding:0 0 25px;border-bottom:1px solid #d9e2ed;font-size:13px}nav a{white-space:normal}ol{padding-left:24px}li{padding-left:5px;margin-bottom:12px}.document-label{font-size:12px;letter-spacing:1.5px;text-transform:uppercase;color:#52677e;margin-bottom:14px}.footer{margin-top:60px;color:#52677e;font-size:13px}
@media(max-width:750px){main{margin:0;border:0;border-radius:0;padding:30px 22px}h1{font-size:29px}th,td{padding:9px;font-size:12px}nav{font-size:12px}}
@media print{@page{size:A4;margin:18mm}body{background:white;font-size:10pt;line-height:1.5}main{margin:0;padding:0;max-width:none;border:0;border-radius:0}h1{font-size:25pt}h2{font-size:16pt;margin-top:24pt}h3{font-size:12pt}h1,h2,h3{break-after:avoid}p{orphans:3;widows:3}nav{display:none}pre,figure,tr{break-inside:avoid}pre{font-size:8pt;padding:10pt}table{font-size:8pt}th,td{padding:7pt}.table-wrap{overflow:visible}a{color:#225b92}svg{max-height:140mm}.footer{font-size:8pt}}
</style></head><body><main><div class="document-label">Manual del producto · Infraestructura Azure</div>
<nav aria-label="Contenido">__NAVIGATION__</nav>__BODY__
<p class="footer">Documento generado desde FUNCIONAMIENTO.md. Goliat - Nexus __VERSION__.</p>
</main></body></html>'''
    destination = Path(destination) if destination is not None else ROOT / ".local/docs/FUNCIONAMIENTO.html"
    destination.parent.mkdir(parents=True, exist_ok=True)
    document = template.replace("__BODY__", body).replace("__NAVIGATION__", navigation).replace("__VERSION__", (ROOT / "VERSION").read_text().strip())
    if local_manual:
        # The standalone manual lives outside the source docs directory.
        prefix = Path(os.path.relpath(ROOT / 'docs', destination.parent)).as_posix()
        def source_link(match):
            parts = urlsplit(match[1])
            if parts.scheme or parts.netloc or not parts.path:
                return match[0]
            return f'href="{prefix}/{match[1]}"'
        document = re.sub(r'href="([^"]+)"', source_link, document)
    destination.write_text(document)
    print(destination)
    return destination


if __name__ == "__main__":
    main()
