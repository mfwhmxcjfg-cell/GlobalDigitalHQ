# Limites de sécurité et périmètre

- Serveur accessible uniquement sur `127.0.0.1`, `Host` strict et `Origin` attendu sur les mutations.
- Chaque exécution produit un jeton propriétaire aléatoire en mémoire, envoyé via page locale et requis via `X-GDHQ-Token` pour les API ; il ne doit pas être exposé en ligne. Il ne protège pas contre un utilisateur local déjà compromis.
- L'aperçu est servi en iframe `sandbox="allow-scripts"` avec CSP interdisant réseau sortant, iframe, formulaires et scripts distants. Aucun exécutable serveur généré par IA n'est lancé.
- Les fichiers générés par IA sont limités à `index.html`, `styles.css`, `app.js`. Garde-fous par motifs (non exhaustifs), contrôle du contrat de fonctionnement, et syntaxe JS avec Node.js avant mise à jour. Des checks statiques ne constituent **pas** un sandbox universel ; ne pas modifier cette politique pour accepter du code arbitraire sans isolation système forte.
- Aucun fournisseur payant n'est configuré. Approver un Gate ne déclenche pas d'achat ou une publication : ces connecteurs sont absents.
- Aucune authentification multi-utilisateur, aucun chiffrement au repos, aucun contrôle d'accès contre les administrateurs locaux, aucun pentest indépendant, aucune certification RGPD. Ne pas exposer `8824` sur un routeur, ngrok ou Internet.
- Aucune installation automatique de skills GitHub ; catalogues en lecture seule.
- Les règles de confidentialité des APIs publiques, cookies et marketing doivent être analysées avant déploiement commercial.
- Les logs ne contiennent pas de jeton propriétaire ; ils peuvent contenir les objectifs de projets. Protéger les dossiers locaux Windows et les sauvegardes.
