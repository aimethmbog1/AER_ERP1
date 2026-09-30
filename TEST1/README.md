# Suivi des dossiers — AER (prototype)

Application Streamlit de digitalisation du suivi des dossiers à l'Agence de l'Électrification
Rurale (AER), conçue en réponse au diagnostic du mémoire : **« Insuffisance de digitalisation et
de centralisation des processus internes de l'A.E.R »** (difficultés de traçabilité, retards de
traitement, dispersion de l'information entre WhatsApp/papier/Excel, manque de coordination).

## Installation

```bash
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

## Lancement

```bash
streamlit run Home.py
```

## Structure du projet

```
Home.py                                    Vue d'ensemble : KPI, dossiers en retard
pages/
  1_📂_Registre_des_dossiers.py            Registre générique : saisie, filtres, édition, CSV
  2_🔀_Transmissions_et_traçabilité.py     Journal des mouvements entre services + délais calculés
  3_📊_Tableau_de_bord.py                  Indicateurs : statuts, retards, charge par service/direction
  4_🏢_Organigramme.py                     Référentiel réel des services (routage), graphique icicle
utils/
  orgchart.py                                Structure réelle de l'AER (Direction Générale, DECDP,
                                              DGOER, DAAF, sous-directions, services, antennes)
  dossiers.py                                Modèle du registre de dossiers + calculs de retard
  transmissions.py                           Journal des transmissions + temps passé par service
  ui.py                                      Composants d'interface & thème partagés
```

## Ce que cette application fait — et ne fait pas

- **Aucun dossier réel n'est préchargé.** Ni le mémoire, ni l'organigramme fourni ne contiennent de
  vrais dossiers, échéances ou statuts : le registre et le journal des transmissions **démarrent
  vides**. C'est un prototype à alimenter (avec des cas réels ou fictifs selon l'usage : démonstration
  académique, test pilote sur un service).
- **Le routage entre services s'appuie sur l'organigramme réel de l'AER** (Direction Générale, les
  3 directions centrales DECDP/DGOER/DAAF avec leurs sous-directions et services, et les 4 antennes
  régionales) — pas sur une liste de services inventée. Deux réserves honnêtes sur la fidélité de cette
  structure sont documentées dans la page Organigramme (une redite apparente de « Service des Marchés »
  dans le texte source, et un léger écart entre notre décompte et la légende officielle de
  l'organigramme).
- **La traçabilité et les délais sont calculés uniquement à partir des dates que vous saisissez** dans
  le journal des transmissions — aucune durée n'est estimée ou inventée.
- **Pas de base de données persistante** : Streamlit ne conserve rien entre deux sessions ou après un
  redéploiement. Téléchargez le registre et le journal en CSV avant de fermer une session, et
  rechargez-les à la reprise via les boutons dédiés.

## Déploiement

Projet prêt pour [Streamlit Community Cloud](https://streamlit.io/cloud) : poussez ce dossier sur un
dépôt Git et pointez le déploiement vers `Home.py`.
