from fastapi import APIRouter, HTTPException
from pathlib import Path
import sys, re

from .state import CURRENT_SPEC

from common.azure_llm import azure_llm_chat

router = APIRouter()

def build_context(q: str, spec: dict) -> str:
    ctx = []
    # mesures pertinentes
    for m in spec["measures"]:
        if re.search(re.escape(m["name"]), q, re.I):
            ctx.append(f"Mesure {m['name']} = {m['expr']}")
    # tables pertinentes
    for t in spec["tables"]:
        if re.search(re.escape(t), q, re.I):
            ctx.append(f"Table présente : {t}")
    # visuels
    for p in spec["pages"]:
        for v in p["visuals"]:
            for fld in v["fields"]:
                if re.search(re.escape(q), str(fld), re.I):
                    ctx.append(f"Champ {fld} utilisé dans la page {p['name']}")
    return "\n".join(ctx) or "Pas de contexte direct trouvé."

@router.post("/api/chat")
async def chat(question: str):
    if CURRENT_SPEC.data is None:
        raise HTTPException(400, "Aucun rapport analysé.")
    context = build_context(question, CURRENT_SPEC.data)
    messages = [
        {"role": "system", "content": "Tu es un expert Power BI."},
        {"role": "assistant", "content": context},
        {"role": "user", "content": question},
    ]
    answer, _ = azure_llm_chat(messages)
    return {"answer": answer}
