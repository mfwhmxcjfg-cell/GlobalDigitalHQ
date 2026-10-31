# Autonomie contrôlée — contrat d'exploitation (31 octobre 2026)

## Statut
PROPOSÉ, non déployé. Aucun agent autonome ni connecteur activé par ce document.

## Architecture
- Orchestrateur par projet, isolé : WEW et Global Digital HQ n'échangent ni secrets ni données sans autorisation.
- Exécution périodique uniquement via workflows configurés et testés, avec identifiant de tâche idempotent, verrou anti-doublon, délai maximal, quota, retry plafonné et file d'échec.
- Journal append-only avec UTC, source, date de collecte, empreinte du contenu, version de la décision, acteur, résultat et statut OBSERVED/CALCULATED/ESTIMATED/NO_DATA.
- Sauvegarde chiffrée, test périodique de restauration et alertes d'échec.
- Mode dégradé : en absence d'API, de source vérifiable ou de budget, marquer INACCESSIBLE et suspendre les décisions dépendantes.
- Owner Gate : approbation obligatoire pour dépenses, publications, prospection, données sensibles, migrations et modifications de production.
- Secrets uniquement dans coffres des plateformes ; jamais dans le dépôt, les journaux, les artefacts CI ni le navigateur.
- Avant d'activer une tâche, démontrer un cycle réel : lancement, logs, sortie, reprise, coût et contrôle d'accès.

## WEW
- Veille 08:00–23:00 Europe/Paris uniquement ; éviter les exécutions de recherche hors plage, y compris après retard de planification.
- Conserver les trois produits Recovery Drill Studio, Price Experiment Notebook et Recommerce Profit Ledger.
- WEW Budget : prévisions J+1 à J+7, solde confirmé séparé du solde projeté, anti-doublon et Decimal.
- Grille W1–W8 : ne pas attribuer de codes sans classeur XLSX accessible.
- Les 47 expertises sont conceptuelles, non des agents opérationnels.

## Budget
- Plafond de dépenses exécutables : 0 EUR tant qu'un montant et un prestataire n'ont pas été validés.
- GitHub Actions, Vercel, Supabase et API IA : contrôler les quotas réels avant tout déclenchement.
- Vercel Hobby peut être incompatible avec un usage commercial ; confirmer le plan et les conditions avant monétisation.

## Conditions de passage à TESTÉ puis DÉPLOYÉ
1. Inventaire exhaustif des workflows, projets, secrets attendus (noms seulement), bases, API et droits.
2. Tests unitaires, intégration, sécurité (dont contrôle d'accès externe) et restauration documentés.
3. Exécution réelle horodatée avec preuve de sortie, coûts et absence d'effet externe non autorisé.
4. Validation du propriétaire pour toute action sensible et vérification post-déploiement.

## Rollback
Désactiver le workflow fautif, révoquer les identifiants concernés, revenir au commit testé et restaurer les données seulement depuis une sauvegarde validée.
