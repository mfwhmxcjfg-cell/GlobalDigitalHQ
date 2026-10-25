## Fiabilité et modèles — 25 octobre 2026

Inventaire en lecture seule des modèles, blocage des références OpenAI retirées avant appel, statut explicite dans le cockpit et neutralisation des workflows génériques non configurés. [État réel, tests, limites et rollback](docs/RELIABILITY_2026-10-25.md). Ce code ne prouve pas un déploiement ou une connexion effective sur Windows.

## Mise à jour 1.5.0 — recherche live

Lire [le guide Recherche live et ressources](docs/LIVE_RESEARCH.md) pour importer les API/MCP, configurer les clés et quotas, installer Playwright sur D: et valider les reprises des agents. Les sources deviennent obligatoires pour le parcours des agents. Aucun connecteur n’est activé par le seul déploiement.

# Global Digital HQ — Cockpit 1.4.0

Écosystème GitHub >= 50 000 étoiles, routage métier, adaptateur Ollama local et trois workflows GitHub Actions manuels. Voir [configuration et limites](docs/GITHUB_ECOSYSTEM.md). Installation Windows à distance non effectuée.

# Global Digital HQ — Cockpit 1.3.1

Sources préparées depuis l’archive Cockpit 1.3.1 fournie par le propriétaire le 16 octobre 2026 : base originale extraite et patch appliqué. Le préparateur ZIP n’est plus nécessaire dans ce dépôt.

Aucun secret ni donnée d’exploitation n’est fourni. Les connecteurs distants restent non implémentés dans cette édition ; une connexion GitHub dans ChatGPT ne les active pas sur Windows. Voir `docs/ETAT_REEL_ET_VALIDATION.md` pour les limites.

## Documentation de la base conservée

**CORRECTIF WINDOWS SANS NODE.JS (r2) :** installer et démarrer Global ne nécessite pas Node. Les modifications JS générées par IA restent verrouillées tant que Node est absent.

**INSTALLATION BUREAU WINDOWS 11 :** lire `GUIDE_INSTALLATION_BUREAU.md` et exécuter `INSTALLER_SUR_BUREAU.cmd`.

# Global Digital HQ Next 1.1 — reconstruction propre

**Statut : pilote local testable, non prêt pour le commerce en production.** Nouveau code Python standard (sans installation de dépendances pour le cœur), construit à partir des besoins de Global Digital HQ Hybrid, et **non** une mise à jour de la branche V12.9.2. L'interface est inspirée du style V8 (menu latéral sombre, cartes et indicateurs), mais le ZIP V8 remis par l'utilisateur ne contenait qu'un raccourci `.lnk` : la fidélité visuelle exacte à V8 reste à vérifier lorsque ses sources seront disponibles.

## Démarrage Windows 11 — sans toucher aux anciennes versions

1. **Extraire intégralement** ce ZIP dans un nouveau dossier, sans écraser Global V8/Hybrid.
2. Double-cliquer `INSTALLER_WINDOWS.cmd`. Il copie cette édition vers `%LOCALAPPDATA%\GlobalDigitalHQ_Next\app` et crée le raccourci de Bureau `Global Digital HQ Next`. Les données sont séparées dans `%LOCALAPPDATA%\GlobalDigitalHQ_Next\data`.
3. Double-cliquer le raccourci. Si Windows affiche un avertissement, vérifier le contenu du `.cmd` avant de l'autoriser. Aucune élévation administrateur n'est normalement nécessaire.
4. Ouvrir **http://127.0.0.1:8824/** dans le navigateur pendant que le lanceur reste ouvert.
5. `Moteurs & réglages` → démarrer LM Studio et charger Qwen3.5 9B, puis `Tester les modèles chargés`, sélectionner le nom EXACT renvoyé par LM Studio et l'enregistrer. Activer ensuite le moteur local. Le serveur LM Studio doit être démarré sous `127.0.0.1:1234`, port local uniquement.
6. Créer un projet, puis cliquer **Créer une démonstration locale** pour obtenir un aperçu utilisable immédiatement, ou **Lancer les agents** pour solliciter réellement le modèle local. Dans ce dernier cas, la réussite dépend de LM Studio et du modèle.

Pour tester : `VERIFIER.cmd`. Pour conserver un audit de vérification toutes les 2 heures, exécuter **volontairement** `scripts\INSTALLER_AUDIT_2H.cmd` (crée une tâche Planificateur Windows ; nécessite une session/ordinateur actif). Exécution manuelle : `scripts\AUDIT_2H.cmd`.

## Capacités réellement codées

- API et UI locales, 40 profils de responsables avec mandat, compétences et sélection par type de projet ; responsables qui délèguent à des employés IA temporaires (brouillons, revue manager et rapport CEO).
- Workflows persistants en SQLite, concertation en deux tours (propositions, revues QA/sécurité/RGPD, synthèse CEO), délégation des tâches aux employés métier et contre-expertise par leur manager **uniquement lorsqu'un modèle LM Studio répond**.
- Trois prototypes originaux et locaux : boutique avec panier simulé, mini-app de tâches (dont projet services), mini-outil de calendrier éditorial. Aucun paiement, commande, recherche externe ni publication.
- Mode expérimental d'amélioration du code via le modèle local. Validation de structure, liste de fichiers autorisés, interdiction de connexions externes, parseur `node --check` obligatoire pour appliquer un patch de JS et sauvegarde avant changement. Si Node.js est absent ou si le patch n'est pas conforme, rien n'est activé.
- Journal, tâches, états bloqués, vérification de la base SQLite, sauvegardes transactionnelles, manifestes SHA-256, contrôle de budget strict (aucune interface réelle de dépense), Owner Gates.
- Migration optionnelle des **métadonnées de projets et métriques** depuis une base V8/Hybrid, en lecture seule, sans reprise de secrets ni de contacts clients. Toutes les métriques importées restent `IMPORTED_UNVERIFIED`.
- Mode OpenAI Agents SDK **facultatif**, dépendance externe non installée automatiquement. Son exécution réelle avec Qwen doit encore être vérifiée sur ton Windows.

## Fonctionnalités NON opérationnelles

L'équivalent complet d'Emergent n'est **pas** encore réalisé : pas de création arbitraire de backend, de stockage cloud partagé, de publication App Store/Play Store, de déploiement de sites, d'authentification multi-utilisateur, de recherche Google Trends/TikTok certifiée, de fournisseurs connectés, de campagnes publicitaires, de vraie vente Shopify ni de pentest externe. Les catalogues MCP sont des **références non activées**, les noms de 40 responsables ne signifient pas 40 modèles exécutés en parallèle. Aucun chiffre commercial n'est inventé.

## Commandes

```powershell
python -m gdhq.cli serve --port 8824
python -m gdhq.cli verify
python -m gdhq.cli audit
python -m gdhq.cli backup
python -m gdhq.cli models
python -m gdhq.cli inspect-legacy --source "C:\chemin\agency.sqlite3"
python -m gdhq.cli import-legacy --source "C:\chemin\agency.sqlite3"
```

La base historique ne change jamais pendant la migration. Sauvegarder les deux dossiers `app` et `data` de la nouvelle édition avant toute restauration. Les modifications de code peuvent nécessiter le redémarrage du programme.

**Politique :** dépenses, achats, publications, prélèvements, utilisation de données clients et API distantes **non exécutables par cette édition**. Les validations Owner Gate n'activent pas d'opérations non implémentées.
