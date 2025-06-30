# frontend/app.py – v7 (récent ➜ haut, mais Q ➜ R dans le bon ordre)

import streamlit as st
import requests
import os

st.set_page_config(page_title="Klint – PBIX Spec & Chat", layout="wide")

st.title("🚀 Klint – PBIX Spec & Chat")
BACKEND = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

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

        # ------------------ Affichage : exchange par exchange (récent ➜ haut)
        chat = st.session_state.chat
        idx = len(chat) - 2  # pointe sur le dernier "user"
        while idx >= 0:
            user_role, user_msg = chat[idx]
            assistant_role, assistant_msg = chat[idx + 1]
            st.chat_message(user_role).markdown(user_msg)
            st.chat_message(assistant_role).markdown(assistant_msg)
            idx -= 2
