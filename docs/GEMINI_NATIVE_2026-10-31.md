# Gemini natif — livraison du 31 octobre 2026

## État réel

L'adaptateur REST Interactions v1 est codé pour le conseil de modèles existant.
Le protocole `gemini_interactions` peut être importé individuellement ou par lot
dans Recherche live, puis autorisé et sélectionné dans un plan existant.
Il transmet du texte sans outil, extrait uniquement les sorties publiques et
refuse les résultats incomplets ou les demandes d'action. Les citations restent
contrôlées par `validate_decision` ; Gemini n'est jamais une source de vérité.

Le test Computer Use supplémentaire est un **appel de proposition uniquement** :
un navigateur neuf affiche le formulaire synthétique fixe, en bloque le réseau,
produit une capture et la soumet une fois à Gemini. Aucun clic retourné n'est
exécuté. Ni page de production, ni compte, ni fichier personnel n'est consulté.
Ce test n'est pas une boucle d'automatisation et ne mesure pas un taux de réussite
sur des missions réelles. Le banc de dix parcours précédent reste distinct.

Statut fournisseur : **NON VÉRIFIÉ**. Aucune clé Gemini n'est présente dans cet
environnement. Aucun appel réel ni coût fournisseur n'a été engagé ici.
Le modèle exact, l'accès du compte, les quotas et le tarif doivent être vérifiés
avant le premier appel. Un abonnement ChatGPT ou Gemini public ne vaut pas clé API.

## Contrôles conservés

- Point de terminaison officiel exact, HTTPS, sans clé dans l'URL ; clé référencée
  par variable d'environnement, jamais contenue dans un manifeste.
- Autorisation et révision courante du connecteur, pause, arrêt d'urgence,
  réservation atomique et quotas quotidiens vérifiés avant le réseau.
- Clé absente : aucun appel et aucune réservation. Appel échoué : réservation
  conservée ; aucune relance automatique. Les erreurs ne recopient pas la réponse.
- `store=false`, sans historique fournisseur chaîné ; cela ne garantit pas une
  absence générale de rétention ou d'utilisation des données par le fournisseur.
- Autorisation séparée `browser_fixture: true` pour transmettre la capture
  synthétique. Modifier cette option révoque l'approbation existante.
- Pas d'exposition des pensées, arguments d'action ou captures dans le rapport.

Les montants réservés sont des bornes comptables locales déclarées par le
propriétaire, **pas des factures observées ni un plafond imposé à Google**.
Vérifier leur caractère conservateur selon modèle, entrée et sortie ; employer
également les limites du compte fournisseur. Le coût réel reste `null`.

## Configuration prête à importer, sans activation automatique

Exemple à adapter avec le modèle accessible au compte et un budget accepté.
Les 0,10 USD ci-dessous sont une réservation illustrative, pas un prix annoncé.

```json
{
  "name": "Gemini - essai isole",
  "kind": "MODEL",
  "url": "https://generativelanguage.googleapis.com/v1/interactions",
  "protocol": "gemini_interactions",
  "model": "gemini-3.8-flash",
  "secret_env": "GEMINI_API_KEY",
  "daily_calls": 1,
  "max_cost_usd": 0.10,
  "daily_budget_usd": 0.10,
  "browser_fixture": false,
  "purpose": "Conseil texte sur preuves publiques, sans execution d'outils"
}
```

La disponibilité de ce modèle sur v1 doit être confirmée ; le guide Computer Use
le cite, mais cela ne prouve pas l'accès de ton compte. Aucun remplacement ou
basculement de routage n'est automatique.

## Sonde isolée facultative

Sans option, la commande ne fait rien :

```powershell
python scripts/probe_gemini_fixture.py
```

Après configuration d'une clé hors Git et installation autorisée de Playwright
1.64.0/Chromium : préparer le manifeste JSON hors du dépôt, avec
`browser_fixture: true`, modèle et réservation appropriés. La commande suivante
autorise **un seul appel** sur capture synthétique. Le dossier cible doit être
nouveau ; le programme refuse toute réutilisation d'une base existante.

```powershell
python scripts/probe_gemini_fixture.py --config D:\GDHQ-Config\gemini-trial.json --trial-home D:\GDHQ-Trials\gemini-001 --confirm GEMINI_SYNTHETIC_PROPOSAL
```

La base séparée conserve l'autorisation et le journal des appels ; aucun projet
existant n'est migré. Sortie attendue : `PROPOSAL_RECEIVED_NOT_EXECUTED` ou
`PROPOSAL_BLOCKED`. Le code retour 0 signifie seulement qu'une proposition de
clic a été reçue, pas que l'action a été autorisée ou exécutée. L'absence d'un
verdict de sécurité fournisseur n'autorise jamais une action. Pour la sonde,
le compteur `actions_executed` reste toujours zéro.

## Fichiers et validation

- `gdhq/gemini.py` : transport natif et sonde sans exécution.
- `gdhq/live.py` : schéma et authentification Gemini, autorisation de capture.
- `gdhq/model_council.py` : routage texte vers l'adaptateur natif.
- `scripts/probe_gemini_fixture.py` : lancement explicite sur base séparée.
- `tests/test_gemini.py` : transport simulé, refus, secret, budgets, protocole.
- `MANIFEST.sha256` : intégrité du paquet mise à jour.

Commandes : `python -m unittest discover -s tests -v`, `node --check web/app.js`,
`python scripts/audit_models.py`, vérification de provenance et de manifeste.
Les tests de transport simulé ne prouvent pas la connectivité Google. L'installation
Windows propriétaire et la boucle Gemini de bout en bout restent NON VÉRIFIÉES.
Rollback : revert de cette livraison ; aucune migration de base de production.

Sources primaires consultées le 31 octobre 2026 :

- https://ai.google.dev/api/interactions-api-v1 — transport et schéma v1.
- https://ai.google.dev/gemini-api/docs/computer-use — outil et environnement.
- https://ai.google.dev/gemini-api/docs/interactions-overview — stockage.

Agent Registry reste DIFFÉRÉ : aucun besoin multiprojet démontré, aucun IAM,
service ou ressource Google Cloud créé. Ce choix ne bloque pas le conseil local.
