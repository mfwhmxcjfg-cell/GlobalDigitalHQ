# Migration depuis Global V8 / Hybrid sans écrasement

Le ZIP `Global Digital HQ.zip` reçu ne contenait qu'un raccourci `.lnk` ; les sources UI exactes de la V8 ne sont pas disponibles. La nouvelle UI reprend donc les couleurs et éléments majeurs **décrits** de V8, pas un clonage pixel parfait.

1. Fermer l'ancienne V8 pour obtenir une base cohérente. Sauvegarder `%LOCALAPPDATA%\GlobalDigitalHQ\data` avant manipulation.
2. Copier la base `agency.sqlite3` ou `gdhq.db` d'origine dans un autre dossier de sauvegarde. Ne pas déplacer l'original.
3. Avec Python 3.12, dans le nouveau dossier : `python -m gdhq.cli inspect-legacy --source "CHEMIN_DE_LA_COPIE.sqlite3"`.
4. Vérifier les projets et le nombre de métriques détectés ; en cas d'incohérence, ne rien importer.
5. Sauvegarder la base du nouveau Global : `python -m gdhq.cli backup`.
6. Exécuter `python -m gdhq.cli import-legacy --source "CHEMIN_DE_LA_COPIE.sqlite3"` après validation.

L'import ne touche pas la base historique, ne réimporte pas les mêmes métriques lors d'une relance, et n'importe aucune clé API, mot de passe, données clients ou config de publication. Les KPIs restent `IMPORTED_UNVERIFIED`, sans prétendre être des chiffres observés et vérifiés par connecteur.
