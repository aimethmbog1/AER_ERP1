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
  5_🔍_Recherche_et_registre_courrier.py   Recherche plein texte + registre chronologique du courrier
                                              (bureau d'ordre)
utils/
  orgchart.py                                Structure réelle de l'AER (Direction Générale, DECDP,
                                              DGOER, DAAF, sous-directions, services, antennes) +
                                              graphe hiérarchique avec rangs et règles de routage
  dossiers.py                                Modèle du registre de dossiers + calculs de retard
  transmissions.py                           Journal des transmissions, validation du routage, sens
                                              (aller/retour), délais impartis, bordereau
  session.py                                 Simulation de poste courant (filtre d'affichage)
  backup.py                                  Sauvegarde / restauration complète (JSON, y compris les
                                              pièces jointes)
  attachments.py                             Pièces jointes (scans) par dossier, en mémoire de session
  ui.py                                      Composants d'interface & thème partagés
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
- **Pas de base de données persistante** : Streamlit ne conserve rien entre deux sessions ou après un
  redéploiement. Utilisez la sauvegarde JSON complète (page d'accueil) avant de fermer une session, et
  restaurez-la à la reprise.
- **Les pièces jointes ne sont pas un vrai coffre-fort documentaire** : elles sont gardées en mémoire de
  session (encodées en base64) et incluses dans la sauvegarde JSON complète — limitez leur taille (5 Mo
  par fichier) et leur nombre (10 par dossier), sous peine de fichiers de sauvegarde très volumineux.

## Déploiement

Projet prêt pour [Streamlit Community Cloud](https://streamlit.io/cloud) : poussez ce dossier sur un
dépôt Git et pointez le déploiement vers `Home.py`.
