# frontend/app.py – v8 (autonome)
# -----------------------------------------------------------------------------
# Ce fichier **se suffit à lui‑même** : on lance la commande
#     streamlit run frontend/app.py
# et il démarre automatiquement le backend FastAPI (uvicorn) dans un thread,
# puis continue l’exécution du front. Les ports/URLs sont internes.
# -----------------------------------------------------------------------------

import os, sys, threading, time, socket, contextlib
import streamlit as st
import uvicorn

# ──────────────────────────────────────────────────────────────────────────────
# 0) Prépare le PYTHONPATH pour trouver le backend et les modules communs
# ──────────────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────────
# 1) Utilitaire : vérifie si un port est libre
# ──────────────────────────────────────────────────────────────────────────────

def port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0

# ──────────────────────────────────────────────────────────────────────────────
# 2) Lance le backend FastAPI **une seule fois**
# ──────────────────────────────────────────────────────────────────────────────
BACKEND_PORT = 8000
BACKEND_URL = f"http://127.0.0.1:{BACKEND_PORT}"

if "_backend_started" not in st.session_state:
    from backend.app.main import app as fastapi_app  # import tardif

    def _run_backend():
        uvicorn.run(
            fastapi_app,
            host="0.0.0.0",
            port=BACKEND_PORT,
            log_level="warning",
        )

    if port_is_free(BACKEND_PORT):
        thread = threading.Thread(target=_run_backend, daemon=True)
        thread.start()
        # attend que le serveur réponde pour éviter les appels 404
        for _ in range(30):
            if not port_is_free(BACKEND_PORT):
                break
            time.sleep(0.1)
        st.session_state["_backend_thread"] = thread
    else:
        st.session_state["_backend_thread"] = None  # déjà lancé

    st.session_state["_backend_started"] = True

# ──────────────────────────────────────────────────────────────────────────────
# 3) Reste du FRONTEND (v7) — inchangé, sauf BACKEND URL
# ──────────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Klint – PBIX Spec & Chat", layout="wide")

st.title("🚀 Klint – PBIX Spec & Chat")
BACKEND = BACKEND_URL  # ← utilise le backend interne

# -----------------------------------------------------------------------------
# 1) SESSION STATE INIT
# -----------------------------------------------------------------------------
for k, v in {
    "chat": [],   # stocke toujours par paires (user, assistant)
    "spec_id": None,
    "spec_func": None,
    "spec_tech": None,
    "pbix_uid": None,
}.items():
    st.session_state.setdefault(k, v)

# -----------------------------------------------------------------------------
# 2) SIDEBAR – Upload PBIX
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("📂 Charger un PBIX")
    pbix = st.file_uploader("Dépose un .pbix **complet** ici", type="pbix")

    if pbix:
        uid = f"{pbix.name}_{pbix.size}"
        if uid != st.session_state.pbix_uid:
            st.session_state.pbix_uid = uid
            with st.spinner("Extraction & rédaction en cours…"):
                try:
                    import requests
                    resp = requests.post(
                        f"{BACKEND}/api/spec",
                        files={"pbix": (pbix.name, pbix.getvalue(), "application/octet-stream")},
                        timeout=600,
                    )
                    resp.raise_for_status()
                except Exception as exc:
                    st.error(f"Erreur backend : {exc}")
                    st.stop()

                data = resp.json()
                st.session_state.update(
                    {
                        "spec_id": data["id"],
                        "spec_func": data["functional"],
                        "spec_tech": data["technical"],
                        "chat": [],
                    }
                )
            st.success("Spécification générée ✅")

# -----------------------------------------------------------------------------
# 3) LAYOUT PRINCIPAL
# -----------------------------------------------------------------------------
col_chat, col_spec = st.columns([1.1, 1.5], gap="large")

with col_spec:
    st.subheader("📄 Spécification fonctionnelle")
    if st.session_state.spec_func:
        st.markdown(st.session_state.spec_func, unsafe_allow_html=True)
        with st.expander("🔧 Détails techniques (JSON)"):
            st.json(st.session_state.spec_tech, expanded=False)
    else:
        st.info("Aucune spécification chargée pour l’instant.")

with col_chat:
    st.subheader("💬 Chat Datamodel")

    if not st.session_state.spec_id:
        st.info("Charge d’abord un PBIX pour activer le chat.")
    else:
        # ------------------ Input (en haut)
        prompt = st.chat_input("Pose ta question…")
        if prompt:
            st.session_state.chat.append(("user", prompt))
            with st.spinner("L’IA réfléchit…"):
                try:
                    import requests
                    r = requests.post(
                        f"{BACKEND}/api/chat",
                        json={"id": st.session_state.spec_id, "question": prompt},
                        timeout=120,
                    )
                    r.raise_for_status()
                    answer = r.json().get("answer", "Réponse vide.")
                except Exception as exc:
                    answer = f"Erreur backend : {exc}"
            st.session_state.chat.append(("assistant", answer))

        # ------------------ Affichage : pairs récentes en haut
        chat = st.session_state.chat
        idx = len(chat) - 2
        while idx >= 0:
            user_role, user_msg = chat[idx]
            assistant_role, assistant_msg = chat[idx + 1]
            st.chat_message(user_role).markdown(user_msg)
            st.chat_message(assistant_role).markdown(assistant_msg)
            idx -= 2
