"""Aide & guide — un assistant **à base de règles** (recherche de mots-clés
dans une base de réponses écrites à l'avance), PAS un vrai modèle de langage
branché sur un service externe. Présenté honnêtement comme tel : l'interface
façon « chat » (st.chat_message/st.chat_input) est réutilisée ici pour son
confort de lecture (question/réponse), pas pour faire croire à une IA
conversationnelle qu'il n'y a pas."""
from __future__ import annotations

import time

import streamlit as st

from utils.ui import inject_base_style, render_sidebar_footer, render_page_header, section_title

inject_base_style()

render_page_header("💬", "Aide & guide",
                    "Réponses aux questions les plus courantes sur l'usage de l'application et les "
                    "règles de routage — pas un assistant IA : un guide à base de règles.")

st.info(
    "Cet assistant **ne repose sur aucun modèle d'IA ni service externe** : il recherche vos mots-clés "
    "dans un jeu de réponses écrites à l'avance sur le fonctionnement de l'application. Pour une question "
    "hors de ce périmètre, consultez le README ou les encarts « ℹ️ » présents sur chaque page.",
    icon="ℹ️",
)

FAQ: list[tuple[list[str], str]] = [
    (["routage", "transmettre", "transmission", "autoris", "niveau", "saut"],
     "**Règle de routage** : depuis un poste, un dossier ne peut être transmis qu'à un subordonné direct, "
     "un poste de même rang, le supérieur hiérarchique direct, ou l'extérieur de l'AER — jamais en sautant "
     "un niveau. Exception assumée : le **Service du Courrier, de la Liaison et des Archives** peut "
     "transmettre vers n'importe quel poste (fonction de bureau d'ordre). Détail complet sur la page "
     "**Transmissions & traçabilité** (encart « Règle de routage appliquée »)."),
    (["retard", "échéance", "délai"],
     "Un dossier est **« en retard »** si son échéance prévue est dépassée et qu'il n'est pas "
     "Traité/Clôturé ni Archivé. Les dossiers en retard apparaissent en rouge sur l'**Organigramme**, en "
     "haut de l'**Accueil**, et dans la section dédiée du **Tableau de bord**."),
    (["pièce jointe", "scan", "fichier", "attache"],
     "Depuis la page **Registre des dossiers**, section « Pièces jointes » : choisissez un dossier, "
     "déposez un fichier (5 Mo max, 10 fichiers max par dossier), puis « Attacher ce fichier ». Les "
     "fichiers sont stockés sur le serveur, pas dans votre navigateur — ils sont donc visibles par tous "
     "les utilisateurs connectés au même serveur."),
    (["poste", "se positionner", "qui suis-je", "simulation"],
     "Le sélecteur « Se positionner comme poste », dans la barre latérale, est une **simulation d'usage**, "
     "pas une authentification réelle : il filtre l'affichage sur les dossiers arrivés à ce poste et "
     "pré-remplit la source lors d'une transmission. Rien n'empêche techniquement de changer de poste à "
     "tout moment."),
    (["sauvegarde", "restaurer", "export", "backup", "json"],
     "Sur la page **Accueil** : téléchargez une sauvegarde JSON complète (registre + transmissions + "
     "pièces jointes) à tout moment, et restaurez-la via le même encart (une confirmation est demandée, "
     "l'opération remplace toutes les données actuelles). L'export Excel, lui, est à sens unique "
     "(lecture/partage), il ne se réimporte pas."),
    (["donnée", "démo", "démonstration", "vide", "réinitialis"],
     "L'application démarre avec un **jeu de démonstration** (300 dossiers, 620 transmissions) pour être "
     "utilisable immédiatement. Pour repartir d'une base vide, allez sur **Paramètres & thème** → "
     "« Réinitialiser les données » (action irréversible, confirmation demandée)."),
    (["audit", "qui a modifié", "journal", "trace"],
     "Le **journal d'audit**, en bas de la page **Transmissions & traçabilité**, trace toute transmission "
     "et toute modification/suppression directe du registre, des pièces jointes ou d'une restauration de "
     "sauvegarde — avec l'horodatage, le poste auteur (si positionné) et l'ancienne/nouvelle valeur."),
    (["thème", "sombre", "clair", "couleur", "dark"],
     "Le thème clair/sombre se change depuis le menu **⋮** (coin supérieur droit) → *Settings* → *Choose "
     "app theme*, ou directement sur la page **Paramètres & thème**, qui explique aussi la palette "
     "utilisée."),
]

DEFAULT_ANSWER = (
    "Je n'ai pas de réponse pré-écrite pour cette question précise. Essayez des mots-clés comme "
    "« routage », « retard », « pièce jointe », « sauvegarde », « audit » ou « thème » — ou consultez "
    "les encarts « ℹ️ » en haut de chaque page, qui documentent les règles métier en détail."
)

SUGGESTIONS = ["Comment fonctionne le routage ?", "Comment restaurer une sauvegarde ?",
               "Comment ajouter une pièce jointe ?", "Qu'est-ce que le journal d'audit ?"]


def _answer(question: str) -> str:
    q = question.lower()
    for keywords, reponse in FAQ:
        if any(kw in q for kw in keywords):
            return reponse
    return DEFAULT_ANSWER


if "aide_messages" not in st.session_state:
    st.session_state.aide_messages = [
        {"role": "assistant", "content": "Bonjour — posez une question sur l'usage de l'application "
                                          "(routage, retards, pièces jointes, sauvegardes, audit, thème...)."},
    ]

for msg in st.session_state.aide_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

section_title("SUGGESTIONS")
cols = st.columns(len(SUGGESTIONS))
clicked = None
for col, s in zip(cols, SUGGESTIONS):
    if col.button(s, width='stretch'):
        clicked = s

prompt = st.chat_input("Votre question...") or clicked
if prompt:
    st.session_state.aide_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.status("Recherche dans la base de réponses...", expanded=False) as status:
            time.sleep(0.35)
            reponse = _answer(prompt)
            status.update(label="Réponse trouvée" if reponse != DEFAULT_ANSWER else "Aucune correspondance exacte",
                           state="complete")
        st.markdown(reponse)
    st.session_state.aide_messages.append({"role": "assistant", "content": reponse})

render_sidebar_footer()
