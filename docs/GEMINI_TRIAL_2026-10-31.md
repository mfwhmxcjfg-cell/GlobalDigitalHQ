# Suite du briefing du 31 octobre — état vérifiable

Périmètre autorisé : inventaire Opus 4.8 Fast, cadrage d'un essai Gemini isolé,
report d'Agent Registry. Aucun connecteur commercial, modèle ou routage de
production modifié. Cette branche part de main et ne reprend pas la PR Terra #2.

## 1. Opus 4.8 Fast — G3 / G7 / G8

Source vérifiée le 31 octobre :
https://platform.claude.com/docs/en/release-notes/overview (annonce du 30 octobre).
Seul `claude-opus-4-8` avec `speed: "fast"` est concerné au 30 novembre 2026.
Le catalogue conserve séparément la date de vérification OpenAI du 25 octobre.

Audit source : recherche dans gdhq, scripts, seed et workflows. Aucune utilisation
trouvée avant ajout de la règle de détection. L'adaptateur Claude existant ne
transmet pas le paramètre `speed` ; aucun remplacement de modèle n'est nécessaire
sur ce chemin. Les proxys et la base Windows ne sont pas accessibles ici : leur
état reste NON VÉRIFIÉ. Le contrôle ne reconnaît que le fournisseur exact et la
combinaison documentée, jamais tous les usages d'Opus 4.8.

La nouvelle règle est visible dans l'inventaire et le cockpit existants. Après
la date limite, elle refuse une configuration concernée avant réservation et
réseau. Elle n'ajoute pas la prise en charge du mode rapide à l'adaptateur.

Lecture seule sur le PC, si nécessaire, depuis le dossier du code installé :

```powershell
python scripts/audit_models.py --database D:\GlobalDigitalHQ\data\global.sqlite3
```

Ce script n'affiche pas les clés, noms de connecteurs, URL ni prompts. Code 1 :
référence retirée ou mode déprécié approuvé à examiner. Code 2 : base manquante
ou illisible. Sans --database, l'audit est uniquement celui du dépôt.

## 2. Banc navigateur préparatoire — G1 / G3 / G4 / G7

Sources : https://ai.google.dev/gemini-api/docs/changelog (30 octobre 2026),
https://ai.google.dev/gemini-api/docs/computer-use.

Le banc exécute dix parcours sur un **formulaire synthétique fixe** : focus,
saisie, clic et vérification du brouillon. Il refuse navigation, shell, actions
inconnues, coordonnées invalides, confirmations non obtenues et dépassements de
pas. L'arrêt d'urgence est vérifié avant/après une action ; une action déjà
exécutée reste tracée. La durée limite est vérifiée entre actions ; elle ne
remplace pas la limite de durée du processus CI.

Le contexte navigateur est neuf, les téléchargements désactivés, les service
workers bloqués, les nouveaux onglets fermés et toutes les requêtes réseau
interceptées/refusées. Une requête vers un domaine .invalid vérifie réellement
l'interception. Aucun compte personnel ni commercial n'est réutilisé.

Ce banc n'accepte pas les instructions d'un modèle. Il ne constitue pas un
navigateur général confiné ni un connecteur Gemini. Aucun succès synthétique ne
doit être interprété comme une performance Gemini. La sortie l'indique :
`HARNESS_VERIFIED_MODEL_NOT_TESTED`, `synthetic: true`, `model_called: false`,
`gemini_success_rate: null`.

```powershell
python scripts/trial_computer_use.py
python scripts/trial_computer_use.py --run-offline-fixture
```

La première commande ne lance rien. La seconde exige Playwright 1.64.0 et
Chromium. Une dépendance absente ou un échec produit BLOCKED, code 2, jamais un
succès. Le job `browser-trial` installe ces dépendances uniquement sur un runner
GitHub hébergé jetable ; aucun secret fournisseur n'y est fourni. Le rapport est
un artefact synthétique conservé sept jours. Les règles de facturation Actions
du compte restent applicables ; aucun moteur IA n'est consommé.

## 3. Ce qui reste bloqué pour le modèle réel

Les variables GEMINI_API_KEY et GOOGLE_API_KEY sont absentes de ce processus.
Le coffre du PC, l'accès du compte Gemini, ses quotas, la tarification effective
et la confidentialité des captures ne sont pas vérifiés. Aucun achat ni import
de clé effectué.

Avant un pilote Gemini réel, il faut un adaptateur API et exécuteur isolé audités,
un budget préalablement réservé et plafonné, les données autorisées, ainsi qu'un
Owner Gate daté, borné et expirant. Une action Gemini `allowed` ne remplace pas
l'autorisation GDHQ. Arrêt obligatoire sur confirmation, doute, panne ou budget.
Ne pas brancher directement ce banc synthétique sur une réponse modèle.

Critères du futur pilote : au moins 9 parcours réels sur 10, aucune action hors
périmètre ni fuite de secret, traces consultables et coûts observés par parcours.
Ces critères n'ont pas encore été mesurés. Aucun statut d'agent actif ajouté.

## 4. Agent Registry — G1 / G3 / G6 : DIFFÉRÉ

Source : https://docs.cloud.google.com/agent-registry/release-notes (30 octobre).
Aucun besoin Google Cloud multiprojet démontré dans le périmètre inspecté.
Aucune API activée, aucun rôle IAM accordé, aucune ressource créée. Réexaminer
uniquement avec plusieurs projets réels, un besoin documenté et un coût approuvé.

## Livraison et retour arrière

Les projets et bases ne sont pas migrés. Les profils métier sont conservés.
Le code est livré en PR, sans déploiement du PC. Retour arrière par revert du
commit de cette PR ; aucune restauration de données nécessaire. La validation
Windows hébergée ne constitue jamais une validation du poste propriétaire.

Limite locale : le pilote Node fourni avec Playwright segfaulte ; le Node du
runtime démarre le pilote, mais Chromium est absent. La tentative de téléchargement
échoue (archive invalide). Le navigateur local reste donc NON VÉRIFIÉ ; les tests
unitaires avec mocks sont séparés du job navigateur réel GitHub Actions.
