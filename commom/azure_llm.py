"""
Wrapper MINIMAL pour appeler Azure OpenAI ChatCompletion.

Variables d’environnement attendues :
- AZURE_OPENAI_KEY
- AZURE_OPENAI_ENDPOINT   (peut être soit 'https://<ressource>.openai.azure.com'
                           soit l’URL déjà complète …/deployments/<id>/chat/completions)
- AZURE_OPENAI_DEPLOYMENT (si l’endpoint n’inclut pas déjà /deployments/…)
- AZURE_OPENAI_API_VERSION (défaut : 2025-01-01-preview)
"""
from typing import List, Dict, Tuple
import os, requests
from dotenv import load_dotenv   # ← NEW
load_dotenv()   

def azure_llm_chat(
    messages: List[Dict],
    model: str | None = None,
) -> Tuple[str, Dict]:
    api_key = os.getenv("AZURE_OPENAI_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", model or "gpt-4o")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")

    if not api_key or not endpoint:
        raise RuntimeError("AZURE_OPENAI_KEY ou AZURE_OPENAI_ENDPOINT manquant dans .env")

    # Construit l’URL si nécessaire
    if "/deployments/" not in endpoint:
        endpoint = (
            f"{endpoint}/openai/deployments/{deployment}/chat/completions"
            f"?api-version={api_version}"
        )

    payload = {"messages": messages, "max_tokens": 1200}
    headers = {"api-key": api_key, "Content-Type": "application/json"}

    resp = requests.post(endpoint, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    return (
        data["choices"][0]["message"]["content"],
        {"x-llm-endpoint": endpoint, "x-llm-deployment": deployment},
    )
