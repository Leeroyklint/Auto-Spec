import json, sys
from pathlib import Path
from typing import Dict
from datetime import date

sys.path.append(str(Path(__file__).resolve().parents[2] / "common"))
from azure_llm import azure_llm_chat

MODEL = "gpt-4o"

def _short(items, n=15):
    return items if len(items) <= n else items[:n] + ["…"]

def generate_narrative(spec: Dict) -> str:
    kpi_lines = "\n".join(
        f"- **{m['name']}** : `{m['expr']}`" for m in _short(spec["measures"])
    )
    page_lines = "\n".join(
        f"- **{p['name']}** ({len(p['visuals'])} visuels)" for p in spec["pages"]
    )
    prompt = f"""
Nous sommes le {date.today():%d/%m/%Y}. Tu es un consultant BI de Klint.
À partir des métadonnées ci-dessous, rédige une spécification fonctionnelle
en cinq sections (Introduction & objectifs, Sources de données, Indicateurs,
Description des pages, Glossaire).

### Tables ({len(spec['tables'])})
{', '.join(_short(spec['tables'], 20))}

### Mesures ({len(spec['measures'])})
{kpi_lines}

### Pages ({len(spec['pages'])})
{page_lines}
""".strip()

    answer, _ = azure_llm_chat([{"role": "user", "content": prompt}], model=MODEL)
    return answer.strip()
