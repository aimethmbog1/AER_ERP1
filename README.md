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
Home.py                                    Vue d'ensemble : KPI, alertes, sélecteur de poste, sauvegarde/restauration
pages/
  1_📂_Registre_des_dossiers.py            Registre générique : saisie, filtres, édition, CSV
  2_🔀_Transmissions_et_traçabilité.py     Journal des mouvements avec routage contraint, retour à
                                              l'émetteur, bordereau, frise chronologique
  3_📊_Tableau_de_bord.py                  Indicateurs, benchmarking des délais par service, rapport
                                              de synthèse exportable
  4_🏢_Organigramme.py                     Référentiel réel + graphe organigramme avec voyants de
                                              statut (vert/jaune/rouge) en temps réel
utils/
  orgchart.py                                Structure réelle de l'AER (Direction Générale, DECDP,
                                              DGOER, DAAF, sous-directions, services, antennes) +
                                              graphe hiérarchique avec rangs et règles de routage
  dossiers.py                                Modèle du registre de dossiers + calculs de retard
  transmissions.py                           Journal des transmissions, validation du routage, sens
                                              (aller/retour), délais impartis, bordereau
  session.py                                 Simulation de poste courant (filtre d'affichage)
  backup.py                                  Sauvegarde / restauration complète (JSON)
  ui.py                                      Composants d'interface & thème partagés
```

## Fonctionnalités professionnelles ajoutées

- **Routage contraint par l'organigramme réel** : un dossier ne peut être transmis qu'à un palier
  directement inférieur, à un poste de même rang, ou en retour vers le supérieur hiérarchique — jamais
  en sautant un niveau. Toute tentative non conforme est bloquée avec un message explicite.
- **Retour à l'émetteur en un clic** : l'application retrouve automatiquement qui a envoyé le dossier
  au poste courant et propose ce retour comme action dédiée, marquée « Retour » dans le journal.
- **Graphe organigramme avec voyants de statut** (page Organigramme) : chaque poste s'allume en
  🔴 rouge (dossier en retard), 🟡 jaune (échéance à ≤ 3 jours) ou 🟢 vert (tout est dans les délais),
  calculé en direct à partir du registre — la vue d'ensemble visuelle demandée pour piloter l'activité.
- **Délai imparti par étape et alerte de dépassement**, en plus de l'échéance globale du dossier.
- **Bordereau de transmission téléchargeable** (texte, prêt à imprimer/signer) à chaque mouvement.
- **Frise chronologique (timeline)** du trajet d'un dossier entre les services.
- **Simulation de poste courant** (barre latérale) : filtre l'affichage sur « mes dossiers » et
  pré-remplit la source d'une transmission — une commodité d'usage, pas une authentification réelle.
- **Sauvegarde/restauration complète en un fichier JSON** (registre + journal), en plus des exports CSV
  par table — pour ne rien perdre d'une session à l'autre.
- **Benchmarking des services** (boîtes à moustaches des délais) pour repérer les goulots
  d'étranglement, et **rapport de synthèse exportable** en Markdown.

## Ce que cette application fait — et ne fait pas

- **Aucun dossier réel n'est préchargé.** Ni le mémoire, ni l'organigramme fourni ne contiennent de
  vrais dossiers, échéances ou statuts : le registre et le journal des transmissions **démarrent
  vides**. C'est un prototype à alimenter (avec des cas réels ou fictifs selon l'usage : démonstration
  académique, test pilote sur un service).
- **Le routage s'appuie sur l'organigramme réel de l'AER**, avec des rangs déduits de la légende
  officielle (« chef de division et conseiller technique = rang directeur », « chef de cellule = rang
  sous-directeur », « chargé d'étude = rang chef de service ») — sauf pour les 4 chefs d'antenne
  régionale, positionnés au même palier que les directeurs de département **pour les besoins du
  routage dans cette application**, conformément à l'exemple donné, mais sans confirmation que ce soit
  la grille indiciaire officielle de l'AER. Deux réserves supplémentaires (redite de « Service des
  Marchés », léger écart de décompte avec la légende officielle) sont documentées dans la page
  Organigramme.
- **La traçabilité et les délais sont calculés uniquement à partir des dates que vous saisissez** —
  aucune durée n'est estimée ou inventée.
- **La simulation de poste n'est pas un contrôle d'accès réel** : rien n'empêche techniquement de
  changer de poste ou d'éditer directement un dossier en dehors du routage validé (l'édition directe du
  registre le signale d'ailleurs explicitement).
- **Pas de base de données persistante** : Streamlit ne conserve rien entre deux sessions ou après un
  redéploiement. Utilisez la sauvegarde JSON complète (page d'accueil) avant de fermer une session, et
  restaurez-la à la reprise.

## Déploiement

Projet prêt pour [Streamlit Community Cloud](https://streamlit.io/cloud) : poussez ce dossier sur un
dépôt Git et pointez le déploiement vers `Home.py`.
