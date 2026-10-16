# Installation sur le Bureau (Windows 11) — édition prête à lancer

Cette archive ne peut pas s’installer automatiquement depuis la conversation : elle doit être lancée une fois sur ton ordinateur. **Ni GitHub ni abonnement API nécessaire pour la partie locale.**

## Installation

1. Télécharger le ZIP et faire **Extraire tout** dans l’Explorateur Windows. Ne pas exécuter les fichiers depuis l’aperçu ZIP.
2. Dans `GlobalDigitalHQ_Next`, double-cliquer sur `INSTALLER_SUR_BUREAU.cmd` (ou `INSTALLER_WINDOWS.cmd`). Ne pas lancer en administrateur : il ne doit pas en avoir besoin.
3. Le programme vérifie Python 3.11+, exécute les tests de code, copie l’application vers `%LOCALAPPDATA%\GlobalDigitalHQ_Next_1_1_Desktop\app` puis crée le raccourci **Global Digital HQ Next 1.1** sur le Bureau.
4. Double-cliquer sur le nouveau raccourci. L’interface s’ouvre normalement à `http://127.0.0.1:8824/`. Garder la fenêtre du serveur ouverte.
5. LM Studio : charger Qwen3.5 9B, `Developer` → `Start Server`, en limitant le serveur à `127.0.0.1:1234`. Dans Global → Moteurs & réglages → Tester les modèles chargés, choisir l’**identifiant exact** et activer le moteur local lorsque tu le souhaites.
6. Cliquer sur `DIAGNOSTIC_BUREAU.cmd` en cas de problème. Une absence de modèle chargé n’empêche pas la création de prototypes de démonstration.

## Isolation et sécurité

- Code installé dans `%LOCALAPPDATA%\GlobalDigitalHQ_Next_1_1_Desktop\app`.
- Données dans `%LOCALAPPDATA%\GlobalDigitalHQ_Next_1_1_Desktop\data`. V8, V12 et Hybrid restent inchangés ; aucun import de données ni de secrets n’est automatique.
- Serveur web et serveur de modèles limités au PC local. Aucune dépense ou publication n’est possible via cette édition pilote.
- Si le port 8824 est déjà utilisé, fermer la précédente instance ; le lanceur n’ouvre pas par erreur une autre application.
- **Les tests sur ton ordinateur restent à valider**. Les tests Python fournis ont été exécutés dans un environnement Linux avant livraison.

## Fonctions non incluses

Ce projet n’est pas un clone complet d’Emergent : les connecteurs réels, le déploiement automatique et le commerce en production restent des développements à effectuer. La liaison de l’OpenAI Agents SDK et les performances de Qwen3.5 9B dépendent de ta machine.

## Audit toutes les deux heures

Pour activer le contrôle périodique demandé auparavant, lancer volontairement `scripts\INSTALLER_AUDIT_2H.cmd` depuis le dossier de l’application installée. Il vérifie le moteur et enregistre un rapport local, sans dépenses ni correction automatique risquée. Le Planificateur de tâches Windows peut demander une autorisation ; vérifier `taskschd.msc`.

## Correction Windows — absence de Node.js (r2)

L'ancien programme d'installation échouait à `test_candidate_restore` sur les ordinateurs sans Node.js, alors que le serveur Global n'utilise que Python.
Dans cette édition, le test vérifie séparément (1) la sauvegarde et la restauration des fichiers avec un contrôle JavaScript simulé et (2) que l'application **refuse** d'appliquer du code IA si Node est absent ou si l'analyse syntaxique échoue.
L'installation et les modèles LM Studio ne nécessitent donc pas Node.js. En revanche, **la fonction d'application automatique des modifications JavaScript IA exige toujours Node.js**. Pour la rendre disponible ultérieurement : installer la version LTS depuis https://nodejs.org/, puis fermer et rouvrir Global.
Le programme d'installation affiche un avertissement non bloquant lorsque Node.js est absent. Ce n'est pas une mise à jour de tes anciennes bases.
