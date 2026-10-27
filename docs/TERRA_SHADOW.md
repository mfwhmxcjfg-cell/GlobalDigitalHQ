# Terra : protocole comparatif isolé — 27 octobre 2026

## État réel

G3 orchestration, G4 Product Factory, G6 observabilité, G7 qualité, G8 livraison.
Le propriétaire a demandé les trois priorités du briefing du 27 octobre : préparer
le comparatif, respecter un plafond total de 2 USD avec une clé protégée, conserver
le routage actuel tant que les critères ne sont pas satisfaits.

Cette livraison prépare et contrôle les données et les résultats **hors ligne**.
Elle ne contient aucun appel payant, n'enregistre aucune clé, ne configure aucun
connecteur et ne touche pas au routage de production. Aucun score modèle réel
n'a été mesuré. La suite modèle reste volontairement vide : les 20 missions de
l'installation Windows ne sont pas accessibles dans cet environnement.

Le moteur actuel `gdhq/model_council.py` utilise Chat Completions pour OpenAI.
Le changer de nom de modèle ne crée pas un adaptateur Responses ni un navigateur.
Le replay visuel est une analyse de captures : il ne valide pas une exécution
Playwright/MCP ou un parcours interactif de bout en bout.

## Sources officielles vérifiées le 27 octobre

- https://developers.openai.com/api/docs/models/gpt-6.1-terra
- https://developers.openai.com/api/docs/pricing
- https://developers.openai.com/api/docs/changelog (annonce du 26 octobre)

Tarif documenté Standard, contexte court : 1 USD/M tokens entrants, 5 USD/M
sortants. Les coûts d'outils et les majorations éventuelles ne sont pas compris.
Les prix et les droits du compte doivent être recontrôlés avant une exécution.
Une disponibilité documentaire ne prouve pas l'accès du compte GDHQ.

## Préparer les vingt missions réelles

Copier `seed/terra_shadow_template.json` dans un répertoire privé hors dépôt, par
exemple `D:\GDHQ-evaluations\terra\suite.json`. Renseigner le modèle de référence
réel, sans le remplacer par Sol si GDHQ utilise un autre fournisseur ou un modèle
local. Ne jamais déposer de données privées dans seed, docs ou les artefacts CI.

Les quatre catégories sont `screenshots`, `products`, `writing`, `interfaces`,
cinq missions chacune. Chaque mission contient :

```json
{
  "id": "identifiant-de-mission-reelle",
  "category": "screenshots",
  "synthetic": false,
  "mission_reference": "projet-et-mission-existants",
  "captured_at": "date-heure-ISO-de-la-capture",
  "prompt": "consigne exact envoyé aux deux modèles",
  "criteria": ["critère métier mesurable", "preuve de la conclusion"],
  "evidence": [{"reference": "URL ou document vérifiable", "observed_at": "date ISO", "excerpt": "extrait constaté"}],
  "assets": [{"reference": "fichier privé de capture", "sha256": "empreinte SHA256 de 64 caractères"}]
}
```

Le schéma vérifie la présence des références ; il ne certifie pas leur vérité,
leur fraîcheur ni la correspondance entre un fichier et une empreinte déclarée.
Le relecteur doit contrôler ces éléments. Toute modification des données figées
invalide les observations précédentes.

Depuis le dossier de code, commande sans réseau et sans lecture de la base :

```powershell
python scripts/evaluate_shadow.py --suite D:\GDHQ-evaluations\terra\suite.json
```

Une suite complète retourne `PREPARED_NOT_EXECUTED`, son SHA256 et les prérequis.
Le modèle vide fourni retourne `BLOCKED`, code 2 : ce n'est pas une panne.
La présence éventuelle d'OPENAI_API_KEY dans ce processus est un booléen ; sa valeur
n'est jamais affichée. Cela ne vérifie pas la clé, son solde ou le coffre Windows.

## Avant un appel externe : conditions bloquantes

1. Vérifier le coffre DPAPI sur le poste exécutant. Ne transmettre aucune clé dans
   le chat, Git, un manifeste ou un prompt. Garder les scopes minimaux.
2. Enregistrer l'Owner Gate daté avec identifiant, expiration, modèles, ensemble de
   données autorisé et plafond global **2 USD pour les deux modèles ensemble**.
   Cette demande autorise le périmètre du comparatif, pas un achat automatique de
   crédits ni une migration de production.
3. Disposer d'un adaptateur Responses vérifié, sans outils ni exécution d'actions.
   Réserver atomiquement le coût maximal avant chaque requête dans un journal
   persistant, incluant sortie, raisonnement, images, erreurs et référence.
   Refuser avant appel si le plafond serait dépassé. Aucune relance automatique
   après timeout : garder la réservation et rapprocher la consommation d'abord.
   **Ce runner payant et cette réservation ne sont pas implémentés par ce module.**
4. Vérifier arrêt d'urgence, disponibilité, quotas et tarification effective du
   compte. Si l'un manque, conserver `BLOCKED`, ne rien appeler.

## Enregistrer et évaluer

Le fichier privé d'observations contient `suite_sha256` et 40 `rows`, une par
couple mission/modèle. Une ligne contient : `case_id`, `model`, `request_id`,
`output_sha256`, `trace_reference`, `reviewer`, `reviewed_at`, `completed: true`,
`cost_status: "RECONCILED"`, `cost_usd`, `latency_ms`, `unauthorized_actions`,
`unsupported_claims` et `criteria_pass` (un booléen par critère).

Les coûts doivent couvrir tous les essais et outils pour la mission, erreurs et
temps morts compris. Le temps est mesuré de bout en bout. Ne pas renseigner zéro
par défaut. L'évaluation est effectuée par un relecteur indépendant des modèles,
si possible en aveugle ; leurs propres déclarations ne sont pas une preuve.

```powershell
python scripts/evaluate_shadow.py --suite D:\GDHQ-evaluations\terra\suite.json --observations D:\GDHQ-evaluations\terra\observations.json
```

Critères cumulés : au moins 18/20 missions Terra acceptées, qualité au moins égale
à la référence, aucune action non autorisée ni affirmation sans preuve dans les
deux bras, économie totale d'au moins 30 %, médiane de latence au plus égale,
coût total au plus 2 USD. Une référence gratuite rend l'économie de 30 %
inatteignable : ne pas inventer un coût évité. Un échantillon de 20 est un pilote,
pas une preuve statistique de fiabilité universelle.

Même si tous les critères passent, le statut est `ELIGIBLE_FOR_OWNER_REVIEW`.
**Aucune promotion automatique** : une nouvelle décision précise du propriétaire
reste nécessaire pour changer le routage. Le code existant, ses connecteurs et
ses sauvegardes restent intacts. Rollback : fermer la PR ou revenir sur son commit ;
aucune migration de base n'est nécessaire.

## Vérification et limites

Les tests unitaires utilisent des fixtures explicitement synthétiques pour
vérifier les refus, les seuils, les identités, le gel des données et l'absence de
promotion. Ils ne représentent pas des résultats Terra réels. Le contrôle de
coût de cet évaluateur est **a posteriori**, pas un plafond de facturation.
Ne pas l'utiliser comme autorisation ni mécanisme d'arrêt d'un runner payant.

Validation locale Linux : `python -m unittest discover -s tests -v`, 130 tests
exécutés, 129 réussis et 1 ignoré (DPAPI réservé à Windows). Vérifications
supplémentaires : `node --check web/app.js`, inventaire hors ligne des modèles
et intégrité MANIFEST. Aucun benchmark fournisseur ni test sur le PC propriétaire.
