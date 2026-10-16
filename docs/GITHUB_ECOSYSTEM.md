# GitHub, agents et déploiement — 1.4.0

## Livré
19 dépôts GitHub évalués le 16 octobre 2026, tous >= 50 000 étoiles à l'instant enregistré. `seed/github_ecosystem.json` contient nombre exact, date, commit amont, licence déclarée par GitHub, provenance et empreintes des sources téléchargées. Ce seuil concerne le dépôt parent, pas chaque skill ou serveur MCP référencé. La recherche est une sélection pertinente, pas une liste exhaustive de GitHub.

Les README et licences autorisés sont conservés dans `third_party/` avec quatre méthodes Superpowers complètes. Ce sont des ressources documentaires, pas les applications intégrales ni des exécutables installés. Les liens sans licence claire et les licences particulières restent référencés sans code recopié. Une licence de dépôt ne garantit pas celle des modèles, données ou services tiers qu'il utilise. Les méthodes originales restent séparées et leur licence conservée ; elles n'élargissent jamais les droits de Global.

L'onglet **GitHub & workflows** affiche les états réels. Quatre workflows sont rattachés aux métiers : preuves, produit, opérations, modèle local. Préparer un workflow crée des tâches manuelles idempotentes, sans appeler les outils. Les prompts des responsables et des employés reçoivent les ressources pertinentes et l'obligation de signaler les preuves manquantes. Les fichiers de méthodes sont consultables dans le dépôt ; le modèle ne reçoit pas automatiquement leur texte intégral.

**Ollama** : adaptateur local codé sur l'API OpenAI compatible, `http://127.0.0.1:11434/v1`. L'interface Réglages permet de le choisir et de tester les modèles. Il ne télécharge aucun modèle. Les noms contenant cloud et les routes distantes sont refusés. L'administrateur doit aussi désactiver les fonctions cloud d'Ollama : le cockpit ne peut attester la configuration interne d'un serveur tiers. Le protocole a été testé avec un serveur local de test ; aucune preuve de connexion à Ollama ou LM Studio sur le PC propriétaire.

## Actions GitHub
Toutes les actions sont **manuelles**, sans déclenchement sur push ni pull request. Les actions tierces sont fixées à un commit, droits GitHub limités à contents:read. Aucun secret de fournisseur nécessaire.

- **Validate and package Global** : tests Python, syntaxe JS, provenance des sources, ZIP privé et SHA-256. Runner GitHub hébergé : quota/facturation du compte à vérifier avant lancement.
- **Local agent drafts on owner runner** : exécute les responsables sélectionnés avec Ollama/LM Studio local. Génère de vrais fichiers brouillons et les joint comme artifacts privés. Ne lit pas la base active du cockpit, ne publie rien, ne fusionne aucun code. Cette voie Actions est distincte du moteur du cockpit ; les sorties doivent être revues et importées manuellement.
- **Deploy Global on owner Windows runner** : tests, sauvegarde SQLite et installation locale après saisie `DEPLOY_LOCAL`. Conserve l'ancienne application. Refuse si Global répond sur le port 8824. Ne redémarre pas le serveur, pour permettre le contrôle avant ouverture. Les bases situées ailleurs via GDHQ_DATA_DIR nécessitent une intervention manuelle.

## Brancher le PC
1. Dans ce dépôt GitHub privé : Settings > Actions > Runners > New self-hosted runner. Choisir Windows x64 et suivre exactement les commandes générées par GitHub. Ne partager aucun token.
2. Exécuter le runner avec le même compte Windows que Global ; ajouter le label **gdhq**. Python 3.11+, Node.js (optionnel pour le déploiement) et Windows PowerShell doivent être disponibles pour ce runner. Utiliser un runner à jour compatible avec les actions référencées.
3. Dans Settings > Environments, créer **gdhq-windows** et, si le plan GitHub le permet, configurer les reviewers obligatoires et limiter à main. Le nom d'environnement seul n'active PAS une approbation. Sur un plan sans protection, conserver le lancement manuel réservé au propriétaire ; ne pas accorder l'accès Actions à des tiers.
4. Fermer Global, sauvegarder ses données, ouvrir Actions > Deploy Global on owner Windows runner > Run workflow depuis main, saisir DEPLOY_LOCAL. Installation ciblée : `D:/GlobalDigitalHQ/app`. Utiliser ensuite `D:/GlobalDigitalHQ/LANCER_GLOBAL.cmd` ; il définit les données et fichiers temporaires sur D:. Une ancienne base Bureau est copiée une seule fois si le dossier de données sur D: est vide, avec conservation des données originales. Le compte du runner détermine LOCALAPPDATA ; choisir le même que celui de Global.
5. Après succès, lancer l'app installée via son LANCER.cmd. Tester /health, le cockpit et un modèle local avant de réactiver le moteur.

Le runner a des droits sur le PC. Aucun workflow de code non approuvé ni de fork ne doit y être déclenché. Aucune instance cloud, aucun déploiement public ou achat de service n'est créé par ces fichiers.

## Retour arrière
Fermer Global. Conserver le dossier app courant sous un autre nom, puis remettre le dossier `app-before-*` indiqué dans `last-deployment.json` à la place de `app`. Les données ne sont pas remplacées par le déploiement. Si une migration ultérieure modifie leur schéma, restaurer la sauvegarde avec Global fermé après contrôle. Les exécutions et déploiements Actions n'ont pas été lancés depuis cette session ; le runner propriétaire n'est pas connecté ici.

## Licences / alternatives
n8n, Dify, Firecrawl, MCP servers, Anthropic Skills et la collection Composio restent des références soumises à vérification des termes applicables ; aucun code de ces sources n'est intégré par cette livraison. Les catalogues MCP ne sont pas un serveur universel installé. CrewAI, LangChain, Langflow, AutoGen et Paperclip sont des pistes d'architecture alternatives : le moteur existant n'est pas remplacé simultanément par tous ces frameworks.

### Migration depuis un disque C: plein
Fermer toutes les instances de Global avant le déploiement. Les bases, leurs WAL et journaux sont copiés vers un dossier temporaire sur D:, sans ouvrir la base originale avec SQLite. Les empreintes sont comparées avant/après et avec les copies ; une modification interrompt la migration. SQLite récupère la copie sur D: puis vérifie son intégrité et celle de la sauvegarde. Les originaux restent en place. Ce contrôle ne remplace pas l’arrêt des processus qui écrivent dans la base. Une base illisible ou invalide bloque la migration : aucune installation vide ne remplace silencieusement les données.
