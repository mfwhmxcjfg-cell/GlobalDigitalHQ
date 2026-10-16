# Validation locale — Global Digital HQ Next 1.1

## Environnement de contrôle

- Exécution dans le conteneur Linux, Python 3.13, Node.js 22 pour vérification syntaxique, sans appel à une API distante.
- Python 3.12 Windows 11, Gestionnaire des tâches Windows et LM Studio réel **non disponibles** dans cet environnement.
- Chromium headless est présent mais la politique de l'environnement renvoie `ERR_BLOCKED_BY_ADMINISTRATOR` pour les navigations HTTP ; aucun essai navigateur réel n'est déclaré réussi.

## Campagne

- Suite Python `unittest` complète, tests des agents managers/employés, bases persistantes, backup, verrou dépenses, isolation HTTP/CSRF, prototypes, migration et reprise après interruption.
- Vérification syntaxique de `web/app.js` et des trois scripts des prototypes avec `node --check`.
- `compileall` sur les modules Python.
- Audit manifeste SHA-256 et `ZipFile.testzip()` au conditionnement.
- Simulation des réponses LM Studio via un double de test. **Aucune génération Qwen3.5 9B réelle n'est certifiée.**

## Anomalies et limitations

- Le serveur Windows, `schtasks`, le planificateur d'audit deux heures, l'installateur sur le Bureau et la migration depuis la véritable base V8 doivent être testés sur ton ordinateur.
- Les outils de publication, données Shopify et sécurité RGPD réelle sont absents ; ce pilote ne doit pas être présenté comme un environnement marchand prêt à produire.
- L'amélioration de code généré via IA requiert Node.js pour analyser la syntaxe avant application et vérifie des contrats structurels ; elle ne garantit pas la correction fonctionnelle du code généré. Il ne faut pas traiter ces contrôles comme un pentest.
- Le modèle Qwen3.5 9B peut dépasser la mémoire disponible ou échouer à suivre les contraintes. Dans ce cas Global doit afficher `BLOCKED` et conserver les anciens fichiers.
