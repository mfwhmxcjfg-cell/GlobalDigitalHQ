# Correctif r2 — installation Windows sans Node.js

## Incident confirmé

Sur Windows 11, `INSTALLER_SUR_BUREAU.cmd` arrêtait l'installation au test `test_candidate_restore`, car `apply_candidate()` refuse (correctement) d'appliquer des fichiers JavaScript générés par IA lorsque `node --check` est indisponible. **Node.js n'est pourtant pas une dépendance du serveur ni de l'interface Global**.

## Corrections

- Le test de sauvegarde/restauration simule explicitement l'outil de syntaxe JavaScript ; il vérifie la logique du cycle sans faire dépendre l'installation de Node.js.
- Deux tests supplémentaires vérifient les comportements sécurisés : sans Node, l'application refuse les modifications IA et conserve les trois fichiers d'origine ; en cas d'échec de syntaxe, elle refuse et restaure l'état initial.
- L'installateur affiche un message clair si Node est absent, **sans bloquer le démarrage du produit**.
- Le code de production conserve la vérification `node --check` obligatoire avant toute application d'un patch JavaScript généré par IA.
- Aucun paiement, accès GitHub ou API cloud n'est nécessaire pour l'installation.

## Résultats de validation dans l'environnement de construction

- 59 tests Python réussis, avec Node installé.
- 59 tests Python réussis avec Node absent de `PATH`.
- Scénario de patch et restauration réelle exécuté avec `node --check` : réussi.
- Vérification des empreintes SHA-256 : réussie.

Ces vérifications sont réalisées sur Linux et ne remplacent **pas** le test de l'installateur `.cmd` sur ton Windows 11.

## Installation

Extraire **complètement** la nouvelle archive `r2`, puis double-cliquer `GlobalDigitalHQ_Next/INSTALLER_SUR_BUREAU.cmd`. Ne plus lancer les fichiers du ZIP `r1` ou d'une version précédente. Les dossiers V8 et Hybrid sont conservés. Si Node manque, Global démarrera, mais la fonction d'application automatique de code JavaScript IA restera bloquée jusqu'à installation de Node.js LTS (`https://nodejs.org/`).

LM Studio est indépendant de Node.js. Après l'installation, démarrer LM Studio avec Qwen3.5 9B et son serveur local `127.0.0.1:1234`, puis régler le modèle dans l'interface Global.
