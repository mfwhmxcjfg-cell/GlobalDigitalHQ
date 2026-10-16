# Global Digital HQ Next 1.1 — logique multiagents inspirée de la vidéo

## Modèle fonctionnel

La vidéo illustre un agent patron (JARVIS) qui délègue à des managers sectoriels (Commercial, Compta, Chantiers). Ces managers dirigent des employés spécialisés (Devis, Mails, Factures, Planning), reçoivent leur travail puis remontent au patron.

Ce principe a été intégré **fonctionnellement** et non uniquement comme une illustration :

- **CEO (« JARVIS »)** : création de plans, conseil multiagents, arbitrage et synthèse.
- **40 managers métier** : catalogue métiers hérité du projet Hybrid, avec un responsable RGPD.
- **Employés IA temporaires par mission** : `workforce_tasks` avec responsables, dépendances, statut et livrables.
- **Messagerie agent à agent** : table `agent_messages` (délégation, mission, livrable, blocage et compte rendu).
- **Double passage** : l'employé rédige un document local, puis son manager le critique via une requête LM Studio distincte.
- **Gouvernance** : les travaux à risque élevé deviennent `NEEDS_OWNER_REVIEW` ; aucune vente, facture officielle, expédition, mail ni réservation réelle.
- **Traçabilité** : les brouillons sont enregistrés dans `data/projects/<id>/team/` et référencés par empreinte SHA-256.

## Organisation adaptée à chaque type de projet

- `services` : Commercial → Devis/Mails ; Compta → Factures ; Opérations → Planning ; Privacy Officer → RGPD.
- `dropshipping` : tendances, boutiques concurrentes, fournisseurs, marges, boutique, contenus, confidentialité et QA.
- `webapp` : besoins, architecture, développement, QA, sécurité et données personnelles.
- `content` : sujets, calendrier, scripts, vidéo et droits.
- `general` : études, périmètre, budget, risques et validation.

**Ce sont des tâches de conception locales**, pas des actions transactionnelles ou des preuves de chiffres d'affaires. Les sources externes ne sont pas encore connectées à ce moteur.

## Représentation des statuts

- `QUEUED` : mission attribuée, jamais exécutée.
- `WORKING` : appel effectif au modèle local en cours.
- `WAITING_DEPENDENCY` : attend les résultats d'un autre employé.
- `REVIEWED_DRAFT` : brouillon produit et critique managériale enregistrée, **contenu non vérifié**.
- `NEEDS_OWNER_REVIEW` : document sensible nécessitant validation humaine.
- `BLOCKED` : erreur lors d'un appel du modèle ou arrêt demandé.

## Fonctionnement avec LM Studio

Dans LM Studio, charge Qwen 3.5 9B, puis démarre le serveur sur `127.0.0.1:1234`. Dans Global → Moteurs & réglages, clique sur **Tester les modèles chargés**, choisis l'identifiant exact et active le moteur.

L'exécution des modèles est **séquentielle (un projet à la fois)** pour limiter le risque de saturation du PC. L'IA n'appelle pas les services externes. La démonstration HTML ne nécessite pas LM Studio, mais les véritables échanges entre employés et managers, si.

## Transparence et limites

- Les 40 responsables ne sont pas 40 instances IA simultanées.
- La sélection du bon workflow est basée sur le type de projet choisi, pas encore sur une optimisation autonome mesurée.
- La revue par un manager IA ne certifie pas la véracité d'une affirmation.
- Les documents produits ne sont jamais envoyés ni émis officiellement.
- La conservation de l'interface V8 à l'identique exige toujours les véritables sources de l'application V8 ; cette édition conserve seulement une interface inspirée de l'organisation précédente.
- Codex CLI, MCP externes et SDK payants ne sont pas exécutés par cette version.

## Validation

Pour tester le workflow en bac à sable sans API distante :

```powershell
py -3.12 -m unittest discover -s tests -v
py -3.12 -m gdhq.cli verify
```

Les tests utilisent des modèles de substitution ; ils n'affirment pas que LM Studio est connecté à ton PC. Lance le vrai modèle puis vérifie les statuts d'un projet `Services, artisanat et chantiers`.

Aucune dépense réelle, publication ou suppression des installations V8 / V12.
