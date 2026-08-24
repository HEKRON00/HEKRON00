#!/usr/bin/env python3
"""
Genera la sección de estadísticas de WakaTime para el README de perfil de GitHub,
consultando directamente el endpoint /summaries (confirmado funcional),
en vez de depender de actions de terceros con endpoints distintos.
"""
import os
import sys
import base64
import json
import urllib.request
from datetime import datetime, timedelta

WAKATIME_API_KEY = os.environ["WAKATIME_API_KEY"]
GH_TOKEN = os.environ["GH_TOKEN"]
GH_REPO = os.environ.get("GH_REPO", "HEKRON00/HEKRON00")
BRANCH = os.environ.get("BRANCH", "main")

def wakatime_get(path):
    key_b64 = base64.b64encode(WAKATIME_API_KEY.encode()).decode()
    req = urllib.request.Request(
        f"https://wakatime.com{path}",
        headers={"Authorization": f"Basic {key_b64}"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def make_bar(pct, width=25):
    filled = round(width * pct / 100)
    return "█" * filled + "░" * (width - filled)

def main():
    end = datetime.utcnow().date()
    start = end - timedelta(days=6)
    data = wakatime_get(f"/api/v1/users/current/summaries?start={start}&end={end}")

    total_seconds = data["cumulative_total"]["seconds"]
    total_text = data["cumulative_total"]["text"]

    lang_totals = {}
    editor_totals = {}
    os_totals = {}
    project_totals = {}

    for day in data["data"]:
        for lang in day.get("languages", []):
            lang_totals[lang["name"]] = lang_totals.get(lang["name"], 0) + lang["total_seconds"]
        for ed in day.get("editors", []):
            editor_totals[ed["name"]] = editor_totals.get(ed["name"], 0) + ed["total_seconds"]
        for o in day.get("operating_systems", []):
            os_totals[o["name"]] = os_totals.get(o["name"], 0) + o["total_seconds"]
        for p in day.get("projects", []):
            project_totals[p["name"]] = project_totals.get(p["name"], 0) + p["total_seconds"]

    def fmt_block(totals, limit=6):
        if not totals:
            return "Sin actividad registrada esta semana"
        items = sorted(totals.items(), key=lambda x: -x[1])[:limit]
        total = sum(totals.values()) or 1
        lines = []
        for name, secs in items:
            pct = secs / total * 100
            hrs = int(secs // 3600)
            mins = int((secs % 3600) // 60)
            time_str = f"{hrs} hrs {mins} mins" if hrs else f"{mins} mins"
            lines.append(f"{name:<20} {time_str:<15} {make_bar(pct)}   {pct:05.2f} %")
        return "\n".join(lines)

    section = f"""![Code Time](http://img.shields.io/badge/Code%20Time-{total_text.replace(' ', '%20')}-blue?style=flat)

**📊 Esta semana me dediqué a**

```text
🕑︎ Zona Horaria: America/Tegucigalpa

💬 Lenguajes:
{fmt_block(lang_totals)}

🔥 Editores:
{fmt_block(editor_totals)}

🐱‍💻 Proyectos:
{fmt_block(project_totals)}

💻 Sistema Operativo:
{fmt_block(os_totals)}
```

*Total: {total_text} esta semana — actualizado automáticamente*
"""

    # Fetch current README
    req = urllib.request.Request(
        f"https://api.github.com/repos/{GH_REPO}/contents/README.md?ref={BRANCH}",
        headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(req) as resp:
        file_data = json.loads(resp.read())

    content = base64.b64decode(file_data["content"]).decode("utf-8")
    sha = file_data["sha"]

    start_marker = "<!--START_SECTION:waka-->"
    end_marker = "<!--END_SECTION:waka-->"
    start_idx = content.index(start_marker) + len(start_marker)
    end_idx = content.index(end_marker)

    new_content = content[:start_idx] + "\n" + section + "\n" + content[end_idx:]

    if new_content == content:
        print("Sin cambios, no se hace commit.")
        return

    body = {
        "message": "chore: actualizar estadísticas de WakaTime",
        "content": base64.b64encode(new_content.encode("utf-8")).decode("utf-8"),
        "sha": sha,
        "branch": BRANCH,
    }
    req = urllib.request.Request(
        f"https://api.github.com/repos/{GH_REPO}/contents/README.md",
        headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github+json"},
        data=json.dumps(body).encode("utf-8"),
        method="PUT",
    )
    with urllib.request.urlopen(req) as resp:
        print("README actualizado:", resp.status)

if __name__ == "__main__":
    main()
