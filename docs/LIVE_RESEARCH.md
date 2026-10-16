# Recherche live et décisions sourcées — GDHQ 1.5.0

## Ce qui change

Le parcours des agents collecte désormais des sources avant les décisions. Sans plan de recherche, source exploitable, modèle disponible ou citation valide, il bloque et crée une demande dans **Recherche live & ressources**. Aucun fait externe n’est remplacé automatiquement par une hypothèse. Les propositions de managers et la synthèse du CEO utilisent un contrat JSON avec des citations exactes contrôlées. Les recommandations restent des inférences à examiner : une citation existante ne prouve pas qu’une conclusion est vraie.

Les 40 fichiers de mandat sont transmis sans la coupe arbitraire à 1 500 caractères. Les employés reçoivent le contenu des livrables dont ils dépendent. Une revue JSON REVISE/BLOCKED ne produit plus un statut de brouillon accepté. Chaque nouvelle recherche régénère les brouillons ; les opérations commerciales restent désactivées.

## Installation sur le PC

1. Fermer Global et lancer une nouvelle exécution **Deploy Global on owner Windows runner**, branche `main`, confirmation `DEPLOY_LOCAL`.
2. Pour les pages dynamiques seulement : exécuter `D:\GlobalDigitalHQ\app\scripts\INSTALLER_RECHERCHE.cmd`. Il installe **Playwright Python 1.64.0** et Chromium dans un environnement séparé sur D:. Cela nécessite Internet, Python et de l’espace sur D:. Les API JSON et pages HTML simples n’en ont pas besoin.
3. Démarrer `D:\GlobalDigitalHQ\LANCER_GLOBAL.cmd`. Le lanceur utilise l’environnement D:\GlobalDigitalHQ\venv lorsqu’il existe.
4. Dans **Moteurs & réglages**, choisir un modèle local, le tester, le sélectionner et enlever la pause. Ou sélectionner des connecteurs MODEL autorisés dans le plan de recherche.
5. Ouvrir **Recherche live & ressources**. Importer les connecteurs, enregistrer leurs clés si nécessaire, puis les autoriser. Choisir un projet, une requête publique, les sources, les modèles facultatifs et les KPI nécessaires. Enregistrer le plan et lancer les agents.

**Déploiement réussi ne signifie pas recherche réussie.** Vérifier une ligne E1/E2 avec une date réelle, puis une analyse avec citations. Le workflow **Diagnose live research on owner Windows** lit l’état installé et les compteurs sans publier les prompts, contenus ni clés. Il ne teste pas les API. Pour cela, le bouton **Collecter une preuve** exécute réellement le connecteur choisi (dans ses quotas).

## Import unitaire ou par lots

Le formulaire simple prend une API JSON GET, une page WEB ou PLAYWRIGHT. La zone JSON accepte un objet ou une liste de 1 à 50 objets ; fractionner les fichiers au-delà de 22 Ko. Un nom existant met à jour le connecteur. Toute modification retire son autorisation. Un lot invalide ne modifie aucun connecteur. L’import ne fait aucun appel réseau.

Ce format est un manifeste GDHQ, pas une prise en charge universelle d’OpenAPI ou de `mcpServers`. Une URL seule ne décrit pas les paramètres, droits, coûts et données attendues de toutes les API. Les serveurs MCP stdio, OAuth et anciens transports SSE demandent encore un adaptateur.

```json
[
  {
    "name": "Recherche Brave",
    "kind": "API_GET",
    "url": "https://api.search.brave.com/res/v1/web/search?q={query}&count=3",
    "secret_env": "BRAVE_API_KEY",
    "auth_header": "X-Subscription-Token",
    "auth_prefix": "",
    "follow_links": true,
    "results_path": "web.results",
    "url_field": "url",
    "daily_calls": 20,
    "max_cost_usd": 0,
    "daily_budget_usd": 0
  },
  {
    "name": "Banque mondiale population France",
    "kind": "API_GET",
    "url": "https://api.worldbank.org/v2/country/FRA/indicator/SP.POP.TOTL?format=json&per_page=1",
    "metrics": [{"name": "population", "path": "1.0.value", "unit": "habitants"}],
    "daily_calls": 5
  }
]
```

L’exemple Brave **n’affirme pas la gratuité du compte** : vérifier son contrat puis renseigner les réservations de coût si nécessaire avant autorisation. La population est un exemple technique, pas une preuve pertinente pour tous les produits. Une valeur API `null` bloque le KPI ; elle n’est jamais remplacée par zéro. Les unités du mapping sont déclarées par le propriétaire : les vérifier dans la documentation de l’API. Les chemins utilisent des clés/indices séparés par des points.

`{query}` est encodé dans l’URL GET. Pour une API de recherche, `follow_links=true` autorise la lecture de trois résultats publics maximum. Ces pages ne reçoivent pas la clé du moteur de recherche et consomment aussi son quota. Les redirections sont refusées : configurer l’URL HTTPS finale ou une autre source si nécessaire.

## Clés

Le JSON contient seulement `secret_env`, jamais la clé. Le coffre Windows chiffre la valeur avec DPAPI pour le compte Windows courant ; utiliser un nom comme `BRAVE_API_KEY`, `CLAUDE_API_KEY` ou `MCP_API_TOKEN`. Les variables d’environnement sont également acceptées. Les clés n’apparaissent ni dans les réponses API du cockpit, ni dans les logs de requêtes. Le fichier chiffré est `data/credentials.dpapi`, exclu de Git. Un autre compte Windows ne pourra pas le déchiffrer ; il faudra réenregistrer les clés.

## MCP de lecture

```json
{
  "name": "MCP recherche",
  "kind": "MCP",
  "url": "https://serveur-exemple.invalid/mcp",
  "tool": "search",
  "arguments": {"query": "{query}"},
  "secret_env": "MCP_API_TOKEN",
  "read_only": true,
  "daily_calls": 10
}
```

Remplacer l’URL et l’outil par ceux du serveur réel. Le client négocie Streamable HTTP (2025-11-25, 2025-06-18 ou 2025-03-26), initialise une session, liste les outils et appelle **uniquement l’outil configuré**. JSON et réponses SSE bornées sont pris en charge, sans reprise des flux interrompus, pagination de tools/list ni OAuth automatique. Les outils sans `readOnlyHint=true` sont refusés. Cette annotation n’est pas une garantie : le propriétaire doit connaître l’outil et lui donner un compte limité à la lecture. Aucun script MCP téléchargé n’est exécuté. Un MCP local exige `local=true` et une URL explicite `http://127.0.0.1:PORT/...`.

## Playwright

Un connecteur PLAYWRIGHT lit une page publique dans un nouveau contexte sans session personnelle. Il autorise les requêtes GET vers le même domaine via le client HTTPS contrôlé, limite le nombre et la taille des ressources, bloque service workers, WebSockets, téléchargements et autres méthodes HTTP. Aucun clic de publication, formulaire de paiement ou authentification n’est automatisé. Les sites qui exigent des domaines tiers, une connexion, un CAPTCHA ou des redirections peuvent rester inaccessibles. Cela doit produire une demande de ressource, pas un résultat inventé. Chromium et cette intégration n’ont pas été exécutés sur le PC propriétaire au moment de la préparation de cette version.

## Modèles : OpenAI compatible, DeepSeek, Kimi, Claude, OmniRoute

```json
{
  "name": "Mon modèle via API ou routeur",
  "kind": "MODEL",
  "url": "https://fournisseur-exemple.invalid/v1/chat/completions",
  "protocol": "openai",
  "model": "identifiant-exact-du-modele",
  "secret_env": "MODEL_API_KEY",
  "output_limit_field": "max_tokens",
  "daily_calls": 40,
  "max_cost_usd": 0.05,
  "daily_budget_usd": 2
}
```

Les prix de cet exemple sont fictifs et doivent être remplacés par une borne correspondant au fournisseur et au modèle. Les conversations peuvent aller jusqu’à 14 000 caractères système, 26 000 caractères utilisateur et 5 000 tokens de sortie. Les quotas et réservations sont atomiques ; une requête échouée consomme sa réservation, car sa facturation peut être ambiguë. Aucun retry automatique.

Pour certains modèles OpenAI, utiliser `output_limit_field=max_completion_tokens`. Le format Responses API n’est pas implémenté. DeepSeek/Kimi ou un routeur doivent exposer le contrat chat/completions configuré. Pour Claude natif : `protocol=anthropic`, URL complète de `/v1/messages`, `auth_header=x-api-key`, `auth_prefix` vide. Pour OmniRoute sur le PC : URL complète de chat/completions sur `127.0.0.1`, `local=true`. Le fait que le routeur soit local n’empêche pas les appels distants/facturables en aval. Aucun OmniRoute n’est installé ni connecté automatiquement et aucune promesse de gratuité n’est reprise.

Le plan peut comparer jusqu’à quatre modèles. Chaque réponse doit citer les mêmes sources et couvrir les KPI requis. Le classement privilégie le nombre de sources citées valides ; un contrôle de contradiction doit accepter la cohérence, sinon la décision reste bloquée. Les analyses divergentes sont enregistrées pour examen. Le modèle retenu produit ensuite les travaux des agents. Prévoir suffisamment d’appels : un parcours complet peut dépasser 25 appels. La majorité des modèles ne constitue jamais une preuve.

Les limites GDHQ sont des **réservations sur coût déclaré**, pas une garantie de la facture réelle. Configurer aussi des limites côté fournisseur. Les abonnements ChatGPT/Claude ne prouvent pas que leurs API sont disponibles ou gratuites. Aucun appel payant n’a été effectué lors de la préparation de cette version.

## Ressources et reprise

Une ressource manquante crée une demande persistante et laisse le projet BLOCKED. Après ajout/configuration/autorisation de la ressource, cliquer **Ressource fournie : valider et reprendre**. La reprise est immédiate si toutes les demandes ouvertes sont validées et si le moteur n’est ni en pause ni en arrêt d’urgence. Si une exécution finit encore, une seule reprise est mise en attente. La nouvelle exécution teste de nouveau les ressources ; une configuration invalide rouvre la demande. Après redémarrage, les tâches interrompues restent bloquées jusqu’à une reprise explicite.

## Preuves et limites

Les extraits collectés sont stockés dans `data/projects/ID/evidence/`, avec URL, date de consultation et SHA256 en SQLite. Une date de consultation n’est pas la date de publication. Les extraits sont bornés à 24 000 caractères, dont 1 800 par source sont transmis dans le dossier commun (8 sources maximum). Les citations doivent correspondre exactement aux extraits transmis. Les sources sont traitées comme des données non fiables, jamais comme des instructions. Les redirections, adresses privées et rebinding DNS sont refusés par le transport public ; les services locaux doivent être explicitement déclarés MCP/MODEL.

Cela vérifie la présence des citations, pas l’implication logique de chaque phrase, l’indépendance réelle des sources ou leur vérité. Une information fausse peut être publiée sur un site et une inférence peut rester incorrecte. Les décisions commerciales finales conservent Owner Gate. Le prototype initial reste fondé sur les gabarits locaux ; cette version n’ajoute ni paiement, ni publication Shopify/Amazon/Etsy, ni génération vidéo automatique.

## Documentation primaire consultée le 16 octobre 2026

- MCP Streamable HTTP : https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
- Playwright Python réseau : https://playwright.dev/python/docs/network
- Playwright Python 1.64.0 : https://github.com/microsoft/playwright-python/releases/tag/v1.64.0
- DeepSeek API : https://api-docs.deepseek.com/
- Kimi API : https://platform.kimi.ai/docs/overview

## Vérification

Les tests couvrent import atomique, autorisations, secrets masqués, quotas concurrents, citations invalides, valeurs KPI absentes, MCP de lecture, protocoles modèles, désaccords, transmission des dépendances et reprise après approbation. Ils utilisent des transports/modèles simulés. Un essai HTTPS public depuis l’environnement de préparation a échoué à la résolution DNS : aucune réussite live sur le PC propriétaire n’est prétendue. Le diagnostic Windows et les preuves datées du cockpit servent à établir cette réussite après déploiement.
