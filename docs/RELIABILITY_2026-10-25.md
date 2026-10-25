# Correctifs de fiabilité du 25 octobre 2026

## Périmètre et état observé

Base distante inspectée : `main`, commit `449a9a6a1ab8d6089342a9c6ca34b706f6492c92`.
La copie de travail isolée a été comparée aux empreintes GitHub : aucun écart sur le snapshot initial.
Les correctifs de l'audit local du 17 octobre, non présents sur main, ne sont pas inclus implicitement.
Les 40 profils du dépôt (CEO compris) et tous les projets, historiques et paramètres sont conservés.

Aucun identifiant retiré n'a été trouvé dans les zones exécutables et configurations du dépôt.
La base active `D:\GlobalDigitalHQ\data\global.sqlite3` n'est pas accessible depuis l'environnement de préparation.
L'absence de référence dans Git ne prouve pas l'absence de configuration retirée sur Windows.

## Fonctionnalités ajoutées

- `seed/model_lifecycle.json` : liste partielle des retraits OpenAI effectifs le 23 octobre, vérifiée le 25 octobre contre https://developers.openai.com/api/docs/deprecations.
- `gdhq/model_lifecycle.py` : blocage des modèles retirés pour l'hôte exact `api.openai.com`, à l'import et avant réservation/appel des connecteurs déjà enregistrés. Aucun choix automatique de remplacement.
- Les modèles locaux et routeurs compatibles ne sont pas assimilés à l'API officielle ; leur disponibilité reste non vérifiée.
- Le cockpit Recherche live affiche le statut de cycle de vie des connecteurs MODEL, distinct de leur autorisation et de leur dernier test.
- `scripts/audit_models.py` : inventaire hors réseau sans démarrer Service, sans migration, sans exposition des URL, clés, noms de variables, prompts ou contenus de projets. `--database` ouvre SQLite avec `mode=ro` et `query_only=ON`.
- Les réservations de coût sont cumulées depuis le journal existant, toutes dates et tentatives confondues. Elles ne sont pas des dépenses ou factures vérifiées.

Les statuts `PROVIDER_UNVERIFIED`, `LOCAL_OR_ROUTER_UNVERIFIED` et `NOT_LISTED_AVAILABILITY_UNVERIFIED` ne signifient jamais connecté ou fonctionnel.
Cette liste datée doit être revue périodiquement ; elle ne couvre pas tous les retraits historiques ou toutes les plateformes.

## Workflows corrigés

Sept modèles de workflows étaient incomplets, sans rapport avec le cœur Python, ou automatiques : AWS, Alibaba, Ada, Docker agent, agent Linux self-hosted, labeler, copilot-setup-steps invalide.
Leur contenu original est conservé sous `docs/quarantined-workflows/*.yml.txt`.
Les fichiers actifs sont devenus des workflows manuels dont le job est explicitement désactivé (`if: false`) et sans permissions.
Ils ne peuvent plus installer, déployer ou injecter des clés automatiquement lors d'un push.
Les restaurer nécessite d'abord une configuration correspondant réellement au projet.

Les workflows utiles gardent leur authentification checkout éphémère, `persist-credentials: false` et leurs actions épinglées.
La validation manuelle inclut désormais un job Windows hébergé (dont DPAPI) et Linux.
Le déploiement Windows reste manuel, limité à main, `DEPLOY_LOCAL`, environnement `gdhq-windows`, application fermée.
Son inventaire préalable montre les connecteurs retirés sans réécrire les paramètres ; un code 1 signale un modèle retiré, un code 2 un audit impossible.
Le diagnostic Windows inclut le même inventaire en lecture seule.

## Vérification et usage Windows

Commandes de préparation :

```text
python -m unittest discover -s tests -v
node --check web/app.js
python scripts/audit_models.py
python -c "from gdhq.ecosystem import verify_sources; assert not verify_sources()"
python scripts/package_release.py
```

Inventaire sur Windows, après mise à disposition du code :

```powershell
Set-Location 'D:\GlobalDigitalHQ\app'
python scripts/audit_models.py --database 'D:\GlobalDigitalHQ\data\global.sqlite3'
```

Code retour : 0 = aucune référence retirée détectée dans le périmètre ; 1 = référence ou connecteur autorisé retiré ; 2 = base inaccessible/invalide. `database=NOT_SUPPLIED` signifie que seuls les fichiers du dépôt ont été examinés.
La lecture SQLite peut nécessiter les fichiers WAL/SHM et les permissions Windows correspondantes ; ne pas employer `immutable=1`, qui masquerait des transactions WAL.

## Éléments non activés

Résultats réellement exécutés dans l'environnement Linux de préparation : 122 tests découverts, 121 réussis, 1 ignoré (DPAPI Windows), zéro échec. Syntaxe JavaScript valide avec Node, 11 workflows YAML analysés sans erreur de structure, provenance des sources vérifiée. L'inventaire du dépôt renvoie zéro référence retirée dans les zones analysées. Aucun test API facturable effectué. Les tests utilisent des services et transports de substitution ; ils ne valident pas la connexion d'un fournisseur réel. Le manifeste initial échouait car sept workflows manquaient : il a été régénéré après correction.

| Recommandation des briefings | État réel et raison |
| --- | --- |
| Jetons GitHub expirants / GitHub App | Les workflows utiles ne persistent déjà pas GITHUB_TOKEN. Aucun PAT de production disponible ici ; pas de modification du compte Windows ou d'une organisation Enterprise inaccessible. |
| Politiques Copilot et métriques | Plan/rôle et usage réel inconnus. Pas de souscription ni d'activation fictive. |
| Shopify UCP, webhooks, jetons expirants | Connecteur Shopify transactionnel absent. Aucun compte ou boutique de développement fourni ; tests externes non réalisés. |
| Pendo, Walmart, Notified, Vultr | Aucun compte/donnée requis vérifié. Pas d'installation sans utilité démontrée. |
| Apper, Creatikk, EBX | Disponibilité d'API/MCP et droits effectifs à vérifier séparément. Aucune URL transformée en intégration prétendument opérationnelle. |
| Windows, DPAPI, LM Studio réel | À valider par les workflows Windows et les preuves du poste ; les tests Linux ne prouvent pas leur fonctionnement. |

## Sauvegarde et rollback

Le script existant de déploiement conserve `app-before-<date>` et une sauvegarde transactionnelle dans `backups/<date>` avant de remplacer le code ; il ne lance pas le serveur.
Cette mise à jour ne migre ni ne remplace les données du propriétaire.
Pour revenir en arrière : fermer Global, conserver le code et les données actuelles, restaurer la copie `app-before-<date>` appropriée puis vérifier l'intégrité et les projets avant reprise.
Ne restaurer une base antérieure que volontairement après comparaison : cela pourrait perdre les changements postérieurs.

Pour une migration de modèle : modifier explicitement le connecteur dans Recherche live, vérifier tarifs et protocole, tester avec un plafond d'appels, examiner qualité/latence/coût, puis autoriser. Aucun alias obsolète n'est silencieusement réécrit.
