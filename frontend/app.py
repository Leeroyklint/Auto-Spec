# frontend/app.py – v3 (chat normal, input fixe en bas)
# -----------------------------------------------------------------------------
#  • Input collé en bas de la fenêtre (CSS)
#  • Messages affichés dans l’ordre chronologique classique :
#      ancien ➜ en haut, nouveau ➜ en bas (style ChatGPT)
#  • Aucun doublon — on affiche immédiatement les deux messages
#    puis on les stocke pour la prochaine exécution.
# -----------------------------------------------------------------------------

import streamlit as st
import requests
import os

st.set_page_config(page_title="Klint – PBIX Spec & Chat", layout="wide")

# -----------------------------------------------------------------------------
# CSS : input fixé en bas + padding bas du main container
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
        /* Input fixe */
        [data-testid="stChatInputContainer"] {
            position: fixed !important;
            bottom: 0;
            left: 350px; /* largeur sidebar par défaut */
            right: 0;
            padding: 0.5rem 1rem 0.75rem 1rem;
            background: var(--background-color);
            border-top: 1px solid var(--secondary-background-color);
            z-index: 101;
        }
        /* Laisse de l’espace pour ne pas masquer le dernier message */
        section.main > div:first-child {
            padding-bottom: 7rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🚀 Klint – PBIX Spec & Chat")
BACKEND = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

# -----------------------------------------------------------------------------
# 1) STATE INIT
# -----------------------------------------------------------------------------
DEFAULTS = {
    "chat": [],
    "spec_id": None,
    "spec_func": None,
    "spec_tech": None,
    "pbix_uid": None,
}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)

# -----------------------------------------------------------------------------
# 2) SIDEBAR – Upload PBIX et génération automatique
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
                        "chat": [],  # reset chat history
                    }
                )
            st.success("Spécification générée ✅")

# -----------------------------------------------------------------------------
# 3) LAYOUT PRINCIPAL : Chat | Spec
# -----------------------------------------------------------------------------
col_chat, col_spec = st.columns([1.1, 1.5], gap="large")

# ---------- SPÉCIFICATION -----------------------------------------------------
with col_spec:
    st.subheader("📄 Spécification fonctionnelle")
    if st.session_state.spec_func:
        st.markdown(st.session_state.spec_func, unsafe_allow_html=True)
        with st.expander("🔧 Détails techniques (JSON)"):
            st.json(st.session_state.spec_tech, expanded=False)
    else:
        st.info("Aucune spécification chargée pour l’instant.")

# ---------- CHAT --------------------------------------------------------------
with col_chat:
    st.subheader("💬 Chat Datamodel")

    if not st.session_state.spec_id:
        st.info("Charge d’abord un PBIX pour activer le chat.")
    else:
        # Affiche l’historique dans l’ordre naturel (ancien -> nouveau)
        for role, msg in st.session_state.chat:
            st.chat_message(role).markdown(msg)

        # Input (fixé en bas via CSS)
        prompt = st.chat_input("Pose ta question…")
        if prompt:
            # 1) Affiche immédiatement la question
            st.chat_message("user").markdown(prompt)

            # 2) Interroge le backend
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

            # 3) Affiche immédiatement la réponse
            st.chat_message("assistant").markdown(answer)

            # 4) Stocke les deux messages pour les prochains reruns
            st.session_state.chat.append(("user", prompt))
            st.session_state.chat.append(("assistant", answer))
