"""backend/main.py – v2
-------------------------------------------------------------
• Ajoute des consignes pour obtenir des réponses pédagogiques
  (explication en français, pas de formule DAX brute sauf demande).
• Légère refacto + constante MAX_JSON pour ajuster la taille du
  contexte transmis au LLM.
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
import tempfile
import json
from typing import Dict

from .extract_pbix import extract_spec
from .generate_narrative import generate_narrative
from common.azure_llm import azure_llm_chat

app = FastAPI(title="Klint PBIX Spec & Chat API", version="2.0")

# ----------------------------------------------------------------------------------------------------------------------
# Cache mémoire : id_spec -> JSON technique (⚠️ non persistant → prévoir Redis pour le multi-instance)
# ----------------------------------------------------------------------------------------------------------------------
CACHE: Dict[str, Dict] = {}
MAX_JSON_LENGTH = 8_000   # caractères de contexte pour le LLM

# ------------------------------------------------------------
# Pydantic Schemas
# ------------------------------------------------------------
class SpecResponse(BaseModel):
    id: str
    functional: str   # markdown
    technical: dict   # json brut


class ChatRequest(BaseModel):
    id: str
    question: str


class ChatResponse(BaseModel):
    answer: str


# ------------------------------------------------------------
# Endpoint SPEC : /api/spec
# ------------------------------------------------------------
@app.post("/api/spec", response_model=SpecResponse)
async def build_spec(pbix: UploadFile = File(...)):
    """Extraction des métadonnées d’un .pbix et génération de la spécification fonctionnelle."""
    # --- 1) Sauvegarde temporaire du fichier ---------------------------------------------------
    try:
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pbix")
        tmp_file.write(await pbix.read())
        tmp_file.close()
    except Exception as exc:
        raise HTTPException(500, f"Erreur lors de la sauvegarde du PBIX : {exc}")

    # --- 2) Extraction technique + rédaction fonctionnelle --------------------------------------
    technical = extract_spec(tmp_file.name)
    functional = generate_narrative(technical)

    # --- 3) Cache & réponse --------------------------------------------------------------------
    CACHE[technical["id"]] = technical
    return {
        "id": technical["id"],
        "functional": functional,
        "technical": technical,
    }


# ------------------------------------------------------------
# Endpoint CHAT : /api/chat
# ------------------------------------------------------------
@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    tech = CACHE.get(req.id)
    if tech is None:
        raise HTTPException(400, "⛔ PBIX non chargé. Recharge d’abord un fichier.")

    question = req.question.strip()
    if not question:
        return {"answer": "Pose une vraie question 😉"}

    # --------------------------- PROMPT LLM ----------------------------------------------------
    system_content = (
        "Tu es un expert Power BI. Tu dois répondre *uniquement* en te basant sur le modèle « GreenTech équipe 1 » "
        "fourni ci-dessous (tronqué pour rester dans la limite) :\n\n" + json.dumps(tech)[:MAX_JSON_LENGTH] +
        "\n\n👉 Si l’utilisateur demande *comment* une mesure est calculée, explique-le en français clair et pédagogique, "
        "sans afficher la formule DAX complète tant qu’il ne la réclame pas explicitement. Utilise des exemples concrets "
        "au besoin (pourcentage, somme, ratio, etc.)."
    )

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": question},
    ]

    answer, _ = azure_llm_chat(messages)
    return {"answer": answer}
