# Architecture de reconstruction

## Modules et dépendances

```
Web (web/index.html, app.js, style.css)
  -> API locale (gdhq/webapp.py)
    -> Use cases (gdhq/service.py)
      -> Workflow / équipe (gdhq/engine.py, roles.py)
        -> LM Studio 127.0.0.1:1234 (providers.py)
        -> Option OpenAI Agents SDK local (sdk_provider.py)
      -> Product Factory (gdhq/builder.py)
      -> Policy & Owner Gate (gdhq/governance.py)
      -> SQLite transactionnel (gdhq/database.py)
      -> Diagnostic et sauvegardes (gdhq/auditing.py)
      -> Migration lecture seule (gdhq/migration.py)
```

Une unique génération active par processus (`ThreadPoolExecutor(max_workers=1)`) pour limiter la mémoire utilisée par Qwen3.5 9B. Les agents sont des rôles métier, pas 40 processus indépendants. Les missions exigent un modèle local chargé. Une erreur de génération n'est jamais interprétée comme une tâche réussie.

## Modèle de données

`projects`, `tasks`, `workforce_tasks`, `agent_messages`, `events`, `decisions`, `gates`, `artifacts`, `metrics`, `knowledge`, `audits`, `settings`, `legacy_imports`. `sqlite3.connect` est toujours fermé dans un `finally`. Bases en WAL + timeout. Les migrations sont additives et non destructives. Projets `IMPORTED_READ_ONLY` non exécutés automatiquement.

## Modèles et outils

Par défaut : API LM Studio OpenAI-compatible (`/models`, `/chat/completions`) avec proxy et redirections interdits. Aucune clé requise. Le mode SDK optionnel appelle `OpenAIChatCompletionsModel` et `Runner` avec tracing désactivé. Aucun outil système ou MCP n'est injecté dans le modèle.

## Workflows

1. Création de projet et tâches déterministes.
2. Collecte de preuves externes `UNVERIFIED` si pas de connecteur certifié.
3. Planification + propositions de responsables selon le secteur.
4. Contre-expertise qualité / sécurité / RGPD.
5. Synthèse CEO documentant les divergences.
6. Génération locale de prototype, tests structurels.
7. Owner Gate pour dépenses, publication et données personnelles.
8. Journal d'audit toutes les deux heures via Windows Task Scheduler si installé.

Le moteur ne publie rien et ne peut pas encaisser de paiement. Les corrections proposées par le modèle doivent être validées par restrictions statiques et `node --check`, suivies d'un checkpoint et d'un rollback possible. Il n'exécute jamais les commandes shell demandées par le modèle.

## Prochaines étapes prioritaires

P0 : validation UI Windows réelle, installer, migrations V8 à blanc, ergonomie des différences V8 ; connexion LM Studio réelle et mesures RAM/latence ; tests Playwright sur ordinateur utilisateur.
P1 : vérification E2E de la boutique et des workflows ; moteurs d'apps serveur en conteneurs confinés, rollback DB ; moteur de tests browsers + sécurité automatisée ; extraction de données avec provenance vérifiable.
P2 : intégrations Shopify/Stripe/suppliers/YouTube sous Owner Gate, confidentialité, RGPD et audits humains avant production.
