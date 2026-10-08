# Suivi des dossiers — AER (prototype)

Application Streamlit de digitalisation du suivi des dossiers à l'Agence de l'Électrification
Rurale (AER), conçue en réponse au diagnostic du mémoire : **« Insuffisance de digitalisation et
de centralisation des processus internes de l'A.E.R »** (difficultés de traçabilité, retards de
traitement, dispersion de l'information entre WhatsApp/papier/Excel, manque de coordination).

**Mise à jour majeure (v2) — passage d'un prototype de démonstration à un outil utilisable en
pilote réel** : la version initiale gardait tout dans `st.session_state`, isolé par session de
navigateur — deux agents ouvrant l'application dans deux onglets différents voyaient chacun un
registre vide et indépendant, ce qui empêchait toute coordination réelle entre services. Les
données vivent depuis dans une base **SQLite partagée** entre tous les utilisateurs connectés au
même serveur, en plus de trois bugs corrigés, d'un **journal d'audit** des modifications directes,
et d'une suite de tests automatisés.

## Version 3 — refonte professionnelle (design system, navigation, animations)

Cette troisième version intègre dans l'application AER les compétences, outils et styles
Streamlit démontrés dans une vitrine de compétences construite séparément dans cette même session
(`developing-with-streamlit` pour la mécanique d'application — navigation, thème, data-display,
performance — et `dataviz` pour la méthode de choix des couleurs de graphique). Rien de la logique
métier existante (routage hiérarchique, calculs de retard, audit, sauvegarde JSON) n'a changé —
seules la présentation, la structure de navigation et l'expérience utilisateur ont été reprises.

**Ce qui a changé concrètement :**

- **Design system par thème natif** (`.streamlit/config.toml`) : palette institutionnelle AER
  (bleu marine + accent teal), déclinée en variante **claire et sombre** (menu ⋮ → *Settings* →
  *Choose app theme*) — remplace l'essentiel du CSS fait main de la v2. Le peu de CSS qui reste
  (`utils/ui.py`) est un recours volontaire et restreint : dégradé de marque de la barre latérale,
  bandeau d'en-tête, badges de statut multicolores (le thème natif ne connaît que 7 couleurs
  nommées), et la couche d'animations — chaque bloc se recalcule à partir du thème actif
  (`st.context.theme`) au lieu de dupliquer une palette figée.
- **Navigation par sections** (`st.navigation`/`st.Page`, dans `streamlit_app.py`) : remplace
  l'ancienne auto-découverte par dossier `pages/` (dépréciée) par quatre sections — *Vue
  d'ensemble*, *Dossiers*, *Pilotage*, *Assistance* — chacune des huit pages vivant maintenant dans
  `app_pages/`.
- **Deux pages supplémentaires** : **Aide & guide**, un assistant à base de règles (recherche de
  mots-clés dans un jeu de réponses écrites à l'avance sur le fonctionnement de l'application —
  explicitement présenté comme tel, **pas** un vrai modèle de langage) ; **Paramètres & thème**,
  qui affiche le thème actif et la palette appliquée, et centralise les actions globales
  (réinitialisation des données, rechargement de la démonstration), chacune derrière une boîte de
  dialogue de confirmation.
- **Data-display enrichi** : compteurs KPI animés (montée en valeur façon tableau de bord), mini-
  graphiques de tendance sur `st.metric` (volume de dossiers reçus sur 14 jours — jamais de
  tendance inventée sur un indicateur dont l'historique n'est pas connu), colonnes à barre de
  progression, graphiques natifs (`st.bar_chart`) là où Plotly n'apportait rien de plus, boîtes de
  dialogue de confirmation avant toute action irréversible (restauration de sauvegarde,
  remplacement du registre par un CSV, réinitialisation).
- **Animations et micro-interactions** : apparition progressive des cartes et sections au
  chargement, pastille « en direct » clignotante sur les indicateurs recalculés à la volée, survol
  avec légère élévation sur les cartes/boutons, confettis et notifications (`st.toast`) après une
  action réussie, indicateur de progression (`st.status`) pendant l'enregistrement d'une pièce
  jointe. Choix assumé (l'utilisateur n'a pas exprimé de préférence entre une approche 100 %
  native/CSS et des composants personnalisés) : une couche CSS/JS scoping restreinte plutôt que des
  composants React sur mesure, pour rester un déploiement Streamlit standard, sans étape de build
  supplémentaire.
- **Jeu de données de démonstration pré-chargé** (`seed_data/aer_demo_300.json`, chargé par
  `utils/demo_data.py` au tout premier démarrage uniquement, base vide) : 300 dossiers et 620
  transmissions réalistes, pour que l'application soit immédiatement représentative plutôt que de
  démarrer sur un registre vide. Choix assumé (là aussi, sans préférence exprimée) : repartir d'une
  base vide reste possible à tout moment depuis **Paramètres & thème** → *Réinitialiser les
  données*.
- **Identité visuelle** : aucun logo officiel de l'AER n'a pu être localisé ni téléchargé en ligne
  (recherche web infructueuse, et cet environnement ne peut techniquement pas télécharger un
  fichier binaire externe arbitraire) — `assets/aer_emblem.svg` et `assets/aer_wordmark.svg` sont un
  emblème **ORIGINAL**, créé pour ce prototype (pas une reconstitution du vrai logo), affiché via
  `st.logo()`. Remplacez ces deux fichiers par les vôtres dès qu'un logo officiel est disponible —
  aucune autre partie de l'application n'a besoin d'être modifiée.
- **Remarque technique sur les icônes** : une première version de cette refonte utilisait des
  icônes Material Symbols chargées depuis Google Fonts dans le CSS personnalisé (bandeau d'en-tête,
  cartes KPI) ; la QA visuelle a montré que le glyphe ne s'affichait pas si le navigateur ne peut
  pas atteindre `fonts.googleapis.com` (réseaux d'entreprise filtrés, environnements sans accès
  internet sortant) — le nom de l'icône s'affichait alors en toutes lettres. Remplacé par des
  émojis (police système, aucune dépendance réseau) pour ces éléments faits main ; les icônes de la
  barre de **navigation**, elles, restent en `:material/...:` et continuent de s'afficher
  correctement, Streamlit les servant depuis ses propres polices embarquées plutôt que depuis
  Google Fonts.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

## Lancement

```bash
streamlit run streamlit_app.py
```

## Tests

```bash
pip install pytest
pytest tests/
```

23 tests : stockage SQLite (y compris la non-collision des numéros de dossier après suppression),
règles de routage hiérarchique de l'organigramme, chargement de chaque page (à vide, avec données,
et — le plus important — **vérification que deux sessions distinctes voient bien le même
registre**, qui est exactement la faille que la v2 corrige), et chargement du point d'entrée réel
(`streamlit_app.py`) avec amorçage du jeu de démonstration.

## Structure du projet

```
streamlit_app.py                           Point d'entrée : thème, logo, amorçage des données de
                                              démonstration, puis st.navigation (4 sections, 8 pages)
app_pages/
  accueil.py                               Vue d'ensemble : KPI animés, alertes, rappels d'échéance
                                              (7 j), sélecteur de poste, sauvegarde JSON + export Excel
  registre.py                               Registre générique : saisie, filtres (dont échéance et
                                              tri), édition, CSV, pièces jointes
  transmissions.py                         Journal des mouvements avec routage contraint, retour à
                                              l'émetteur, bordereau, frise chronologique, et le
                                              JOURNAL D'AUDIT (qui a modifié quoi, quand)
  tableau_de_bord.py                       Indicateurs (st.metric + mini-tendances), benchmarking des
                                              délais par service, rapport de synthèse exportable
  organigramme.py                          Référentiel réel + graphe organigramme avec voyants de
                                              statut (vert/jaune/rouge) en temps réel
  recherche.py                             Recherche plein texte + registre chronologique du courrier
                                              (bureau d'ordre)
  aide_assistant.py                        NOUVEAU — guide à base de règles (pas une IA), suggestions
  parametres_theme.py                      NOUVEAU — thème actif, palette, réinitialisation des données
utils/
  db.py                                      Stockage SQLite partagé et persistant (voir section
                                              dédiée) : connexion mise en cache par processus, schéma,
                                              CRUD, journal d'audit
  orgchart.py                                Structure réelle de l'AER (Direction Générale, DECDP,
                                              DGOER, DAAF, sous-directions, services, antennes) +
                                              graphe hiérarchique avec rangs et règles de routage
  dossiers.py                                Modèle du registre de dossiers + calculs de retard ;
                                              lit/écrit dans utils/db.py
  transmissions.py                           Journal des transmissions, validation du routage, sens
                                              (aller/retour), délais impartis, bordereau ; lit/écrit
                                              dans utils/db.py
  session.py                                 Simulation de poste courant (filtre d'affichage)
  backup.py                                  Sauvegarde / restauration complète (JSON, y compris les
                                              pièces jointes) — reste le filet de sécurité ultime
  attachments.py                             Pièces jointes (scans) par dossier — métadonnées en base,
                                              fichiers sur disque
  exports.py                                 Export Excel multi-feuilles (registre, transmissions,
                                              pièces jointes, journal d'audit)
  ui.py                                      NOUVEAU (v3) — design system : thème clair/sombre
                                              theme-aware, animations, badges, KPI, logo
  demo_data.py                              NOUVEAU (v3) — amorçage et réinitialisation du jeu de
                                              démonstration
.streamlit/config.toml                      NOUVEAU (v3) — thème natif Streamlit (clair + sombre)
assets/                                      NOUVEAU (v3) — emblème et lockup AER (originaux, voir
                                              plus haut)
seed_data/aer_demo_300.json                 NOUVEAU (v3) — 300 dossiers / 620 transmissions de
                                              démonstration
tests/                                       23 tests (pytest + streamlit.testing.v1.AppTest)
  conftest.py                                Redirige la base SQLite vers un répertoire temporaire
  test_db.py                                 Stockage, non-collision des numéros, cascade de suppression
  test_orgchart.py                           Règles de routage hiérarchique
  test_pages.py                              Chargement de chaque page + partage entre deux sessions +
                                              amorçage de la démonstration depuis streamlit_app.py
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
  vrais dossiers, échéances ou statuts. Depuis la v3, l'application démarre avec un **jeu de
  démonstration fictif** (300 dossiers, 620 transmissions, générés pour être réalistes) plutôt
  qu'un registre vide, pour être immédiatement représentative lors d'une présentation ou d'un
  pilote — repartir d'une base vide reste possible à tout moment (page **Paramètres & thème** →
  *Réinitialiser les données*). Dans tous les cas, c'est un prototype à alimenter avec de vrais cas
  (démonstration académique, test pilote sur un service), jamais un accès à un vrai système
  d'information existant.
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
dépôt Git et pointez le déploiement vers `streamlit_app.py`. Lisez d'abord la section « Stockage partagé et
persistant » ci-dessus — sur Community Cloud spécifiquement, le disque n'est pas persistant d'un
redéploiement à l'autre, donc la sauvegarde JSON régulière reste nécessaire pour ne rien perdre. Pour un
usage pilote réel avec plusieurs agents, un hébergement avec disque persistant (VM de l'AER, PaaS avec
volume) est recommandé.
