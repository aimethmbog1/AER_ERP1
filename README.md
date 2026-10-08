# Suivi des dossiers — AER (prototype)

Application Streamlit de digitalisation du suivi des dossiers à l'Agence de l'Électrification
Rurale (AER), conçue en réponse au diagnostic du mémoire : **« Insuffisance de digitalisation et
de centralisation des processus internes de l'A.E.R »** (difficultés de traçabilité, retards de
traitement, dispersion de l'information entre WhatsApp/papier/Excel, manque de coordination).

**Mise à jour majeure — passage d'un prototype de démonstration à un outil utilisable en pilote
réel** (voir la section dédiée plus bas pour le détail complet) : la version initiale gardait tout
dans `st.session_state`, isolé par session de navigateur — deux agents ouvrant l'application dans
deux onglets différents voyaient chacun un registre vide et indépendant, ce qui empêchait toute
coordination réelle entre services. Les données vivent désormais dans une base **SQLite partagée**
entre tous les utilisateurs connectés au même serveur, en plus de trois bugs corrigés, d'un
**journal d'audit** des modifications directes, de quelques fonctionnalités supplémentaires, et
d'une suite de tests automatisés (22 tests). Rien de tout cela ne change la philosophie du projet :
toujours aucun dossier réel préchargé, toujours honnête sur ses limites.

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

## Tests

```bash
pip install pytest
pytest tests/
```

22 tests : stockage SQLite (y compris la non-collision des numéros de dossier après suppression),
règles de routage hiérarchique de l'organigramme, et chargement de chaque page (à vide, avec
données, et — le plus important — **vérification que deux sessions distinctes voient bien le même
registre**, qui est exactement la faille que cette refonte corrige).

## Structure du projet

```
Home.py                                    Vue d'ensemble : KPI, alertes, rappels d'échéance (7 j),
                                              sélecteur de poste, sauvegarde JSON + export Excel
pages/
  1_📂_Registre_des_dossiers.py            Registre générique : saisie, filtres (dont échéance et
                                              tri), édition, CSV
  2_🔀_Transmissions_et_traçabilité.py     Journal des mouvements avec routage contraint, retour à
                                              l'émetteur, bordereau, frise chronologique, et le
                                              JOURNAL D'AUDIT (qui a modifié quoi, quand)
  3_📊_Tableau_de_bord.py                  Indicateurs, benchmarking des délais par service, rapport
                                              de synthèse exportable
  4_🏢_Organigramme.py                     Référentiel réel + graphe organigramme avec voyants de
                                              statut (vert/jaune/rouge) en temps réel
  5_🔍_Recherche_et_registre_courrier.py   Recherche plein texte + registre chronologique du courrier
                                              (bureau d'ordre)
utils/
  db.py                                      NOUVEAU — stockage SQLite partagé et persistant (voir
                                              section dédiée) : connexion mise en cache par processus,
                                              schéma, CRUD, journal d'audit
  orgchart.py                                Structure réelle de l'AER (Direction Générale, DECDP,
                                              DGOER, DAAF, sous-directions, services, antennes) +
                                              graphe hiérarchique avec rangs et règles de routage
  dossiers.py                                Modèle du registre de dossiers + calculs de retard ;
                                              lit/écrit désormais dans utils/db.py
  transmissions.py                           Journal des transmissions, validation du routage, sens
                                              (aller/retour), délais impartis, bordereau ; lit/écrit
                                              désormais dans utils/db.py
  session.py                                 Simulation de poste courant (filtre d'affichage)
  backup.py                                  Sauvegarde / restauration complète (JSON, y compris les
                                              pièces jointes) — reste le filet de sécurité ultime
  attachments.py                             Pièces jointes (scans) par dossier — métadonnées en base,
                                              fichiers sur disque (plus en mémoire de session)
  exports.py                                 NOUVEAU — export Excel multi-feuilles (registre,
                                              transmissions, pièces jointes, journal d'audit)
  ui.py                                      Composants d'interface & thème partagés
tests/                                       NOUVEAU — 22 tests (pytest + streamlit.testing.v1.AppTest)
  conftest.py                                Redirige la base SQLite vers un répertoire temporaire
  test_db.py                                 Stockage, non-collision des numéros, cascade de suppression
  test_orgchart.py                           Règles de routage hiérarchique
  test_pages.py                              Chargement de chaque page + partage entre deux sessions
```

## Circuit d'entrée d'un dossier — le service courrier comme porte d'entrée

Conformément au fonctionnement réel décrit : **« les dossiers entrants passent par le service courrier et
celui-ci achemine vers les postes concernés »**.

- Sur la page **Registre**, un nouveau dossier propose par défaut le canal **« Service du Courrier
  (bureau d'ordre) »** : il est alors enregistré au **Service du Courrier, de la Liaison et des
  Archives**, et une première transmission automatique « Externe → Service du Courrier » est journalisée
  pour amorcer la traçabilité, à la date de réception saisie.
- Un canal **« Dépôt direct au service concerné »** reste disponible pour un dossier d'origine interne
  (ex. note initiée directement par un service), qui n'a pas de raison de transiter par le courrier.
- Sur la page **Transmissions**, le Service du Courrier bénéficie d'une **exception assumée** à la règle
  de routage hiérarchique : il peut acheminer un dossier vers **n'importe quel poste**, quel que soit son
  rang (fonction réelle d'un bureau d'ordre), alors que tout autre service reste limité à ses
  subordonnés, ses pairs et son supérieur direct. Cette exception est codée dans
  `utils/orgchart.allowed_destinations()` et documentée dans son docstring, ainsi que rappelée dans
  l'interface (pages Registre, Transmissions, Organigramme).

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
- **Recherche plein texte** (page 5) sur le registre et les commentaires de transmission.
- **Registre chronologique du courrier** (page 5) : vue « bureau d'ordre » des dossiers reçus par le
  service courrier, dans l'ordre d'arrivée, exportable en CSV.
- **Pièces jointes (scans)** par dossier (page Registre), incluses dans la sauvegarde JSON complète.
- **Champ « Référence externe »** par dossier : note libre pour noter, si besoin, le numéro d'un dossier
  correspondant dans un autre système — sans aucune vérification ni liaison automatique.
- **Types de dossier étendus** (RH/Carrière, comptable/budgétaire, état civil) pour classer un dossier
  selon sa nature administrative.

## Une application « inspirée de », pas connectée à AIGLES, PATRIMOINE, SYSTAC/SYGMA, SIGEC ou Maarch Courrier

Le mémoire et les échanges avec l'utilisateur citent plusieurs systèmes d'information de l'État
camerounais : **AIGLES** (carrières et soldes des agents publics, depuis 2025), **PATRIMOINE** (opérations
comptables de l'État, depuis 2022), **SYSTAC/SYGMA** (consultation des décisions et contrôle des échanges
comptables), **SIGEC** (état civil, porté par le BUNEC), et le logiciel **Maarch Courrier** (gestion
documentaire et courrier, utilisé par certaines administrations camerounaises).

**Il faut être clair sur ce que cette application peut honnêtement faire vis-à-vis de ces systèmes :**

- **Aucune connexion, API ou accès réel** à AIGLES, PATRIMOINE, SYSTAC/SYGMA, SIGEC ou Maarch Courrier
  n'existe ni n'est simulée ici. Ce sont des systèmes de l'État, dont l'accès est réservé et dont cette
  application ne dispose d'aucune documentation technique, identifiant ou API — prétendre s'y connecter
  serait faux.
- Ce qui a été repris, ce sont des **fonctions génériques que ces systèmes rendent visibles dans leur
  description** et qui sont, elles, réellement réalisables dans ce prototype Streamlit sans accès à un
  système tiers : la numérisation/pièces jointes et la recherche plein texte et le registre chronologique
  du courrier (inspirés de la description de Maarch Courrier), ainsi qu'un simple champ de référence
  croisée facultatif (pour un usage du type « ce dossier correspond au numéro X dans AIGLES/PATRIMOINE »,
  purement déclaratif, non vérifié).
- Les nouveaux types de dossier (RH/Carrière, comptable/budgétaire, état civil) reprennent le **découpage
  fonctionnel** que ces systèmes couvrent (agents publics, comptabilité publique, état civil), sans lien
  avec les logiciels eux-mêmes — ce sont des catégories de classement internes à l'AER.
- **Aucun chiffre cité par l'utilisateur au sujet de ces systèmes** (date de mise en service, gain de temps
  de 45 à 15 minutes dans l'Est, etc.) n'est repris comme une donnée de cette application : ce sont des
  informations sur des systèmes externes, non vérifiées ici, et sans rapport avec les dossiers réellement
  saisis dans ce prototype.
- « Mettre l'application au-dessus de AIGLES » n'a de sens honnête que pour son **propre périmètre**
  (suivi et traçabilité des dossiers internes à l'AER) : cette application ne gère ni la solde, ni les
  carrières, ni la comptabilité publique, ni l'état civil — ce n'est pas son rôle, et le prétendre serait
  trompeur.

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
- **Base de données partagée et persistante (SQLite)**, avec une limite honnête à connaître : voir la
  section « Stockage partagé et persistant » ci-dessous. La sauvegarde JSON complète (page d'accueil)
  reste le filet de sécurité ultime, surtout si l'hébergement choisi ne garantit pas un disque persistant.
- **Les pièces jointes ne sont pas un vrai coffre-fort documentaire** : elles sont gardées sur le disque
  du serveur (à côté de la base SQLite) et incluses dans la sauvegarde JSON complète — limitez leur
  taille (5 Mo par fichier) et leur nombre (10 par dossier).

## Stockage partagé et persistant (SQLite) — le changement le plus important de cette refonte

**La faille corrigée** : la version initiale gardait tout dans `st.session_state`, isolé **par session
de navigateur**. Deux agents de l'AER ouvrant l'application dans deux onglets différents voyaient donc
chacun un registre vide et indépendant — ce qui contredisait l'objectif même de l'outil (coordination et
traçabilité partagées entre services). Les données vivent désormais dans un fichier SQLite unique
(`utils/db.py`), partagé par tous les utilisateurs connectés au **même processus serveur** (la connexion
est mise en cache par `st.cache_resource`, donc un seul objet, réutilisé par toutes les sessions), avec
le mode WAL pour des écritures concurrentes raisonnables en usage pilote (quelques dizaines d'utilisateurs
simultanés, pas une charge de production à grande échelle).

**Limite honnête à connaître avant un déploiement réel** : ce mécanisme partage les données entre tous
les utilisateurs d'UN SEUL processus Streamlit en cours d'exécution, sur un seul serveur (pas de
réplication multi-instance : SQLite ne s'y prête pas). Il ne survit pas non plus à un redémarrage si le
disque qui contient le fichier `.db` n'est pas lui-même persistant — **c'est le cas sur Streamlit
Community Cloud**, dont le système de fichiers est réinitialisé à chaque redéploiement ou réveil de
veille. Pour un usage pilote réel durable :

- hébergez l'application sur un serveur où le répertoire `data/` est un emplacement qui survit aux
  redémarrages (volume Docker, VM de l'AER, disque persistant d'un PaaS) ;
- sauvegardez régulièrement le fichier `.db`, ou utilisez l'export JSON complet (page d'accueil) ;
- le chemin de la base est configurable via la variable d'environnement `AER_DOSSIERS_DB_PATH` (et
  `AER_DOSSIERS_ATTACHMENTS_DIR` pour les pièces jointes), par défaut `data/suivi_dossiers.db` à la
  racine du projet.

## Journal d'audit — qui a modifié quoi, quand

Nouvelle section en bas de la page **Transmissions & traçabilité**. Toute transmission, tout
ajout/modification/suppression direct du registre ou des pièces jointes, et toute restauration de
sauvegarde sont désormais journalisés (horodatage, champ modifié, ancienne/nouvelle valeur, poste
auteur). Cela comble un trou de traçabilité réel de la version initiale : une modification de statut ou
de poste destinataire faite directement dans le tableau du Registre (plutôt que via une transmission en
bonne et due forme) n'était tracée nulle part.

## Corrections apportées lors de cette refonte

- **Collision de numéro de dossier après suppression** : l'ancien calcul (`len(df) + 1`) pouvait
  réattribuer le numéro d'un dossier supprimé à un nouveau dossier. Le numéro est désormais basé sur
  l'identifiant auto-incrémenté interne de la base, qui n'est jamais réutilisé.
- **Délai imparti de 0 jour silencieusement ignoré** : `0` étant une valeur « fausse » en Python,
  l'ancien code traitait un délai de 0 jour comme « aucun délai ». Remplacé par une case à cocher
  explicite (« Fixer un délai imparti ») sur la page Transmissions.
- **Validation des dates** : un avertissement s'affiche désormais si l'échéance prévue saisie est
  antérieure à la date de réception.

## Fonctionnalités ajoutées lors de cette refonte

- **Rappels d'échéance à 7 jours** sur la page d'accueil (en plus du seuil de 3 jours déjà utilisé pour
  les voyants de l'organigramme), pour anticiper plutôt que seulement constater un retard.
- **Filtres avancés sur le Registre** : échéance avant une date donnée, tri par échéance la plus proche
  ou par date de réception la plus récente.
- **Export Excel multi-feuilles** (registre, transmissions, pièces jointes, journal d'audit), en plus de
  la sauvegarde JSON et des exports CSV par table — pratique pour partager un instantané à la hiérarchie
  sans donner accès à l'application elle-même.

## Déploiement

Projet prêt pour [Streamlit Community Cloud](https://streamlit.io/cloud) : poussez ce dossier sur un
dépôt Git et pointez le déploiement vers `Home.py`. Lisez d'abord la section « Stockage partagé et
persistant » ci-dessus — sur Community Cloud spécifiquement, le disque n'est pas persistant d'un
redéploiement à l'autre, donc la sauvegarde JSON régulière reste nécessaire pour ne rien perdre. Pour un
usage pilote réel avec plusieurs agents, un hébergement avec disque persistant (VM de l'AER, PaaS avec
volume) est recommandé.
