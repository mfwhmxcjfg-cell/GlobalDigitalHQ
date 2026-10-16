# État observé — 15 octobre 2026

Source : GlobalDigitalHQ_Next_1_1_CORRECTIF_NODE_OPTIONNEL_Windows11_r2.zip, version retrouvée du 15 octobre. Le poste Windows et sa base active ne sont pas accessibles depuis cette session.

| Domaine | Avant | Livraison |
|---|---|---|
| Agents | 40 profils, catalogue seulement dans la vue équipe | Statut dérivé des tâches, affectations et dernière activité |
| Projets | Création, workflows et prototypes locaux | Conservés ; rattachement des notes, mesures et tâches |
| Tâches | Étapes automatiques et employés | Suivi manuel distinct avec transitions contrôlées et revue humaine |
| Mémoire | Table knowledge peu exposée | Consultation et ajout de notes déclarées par projet |
| Gates | Décisions locales persistées | Conservées ; attente affichée en orange ; aucun effet externe |
| Paramètres | Pause, arrêt, fournisseur local, modèle | Conservés ; aucun secret distant demandé |
| Connecteurs | Libellés de catalogue | Capacité et absence de connexion explicites ; alternatives manuelles |
| KPI | API de saisie existante | Écran de saisie et lecture, valeurs finies, provenance déclarée |
| Journal | Événements techniques | Ajouts manuels et transitions tracés |

## Validation effectuée
66 tests Python réussis sur une base temporaire, incluant 7 tests ajoutés pour les tâches, notes, KPI et erreurs. Syntaxe JavaScript validée avec Node. Tests HTTP existants : hôte, origine, jeton, accès, dépenses bloquées. Les tests ne constituent pas une validation visuelle navigateur, une installation Windows ou une connexion réelle à LM Studio.

## Limites à ne pas confondre avec un système terminé
Le cockpit local est amélioré ; l'entreprise autonome multicanal reste à intégrer. Aucune preuve de données commerciales, d'agents actifs sur le PC, de publication ou de revenus. Apper.io et Creatikk.io n'ont pas de capacité callable disponible ici. Une application présente dans ChatGPT n'est pas une connexion du runtime Windows.
La mémoire ajoutée n'est pas automatiquement utilisée dans les prompts. Le registre de connecteurs est informatif. Les gates existantes portent sur une catégorie d'action et non sur un devis immuable : ne pas les réutiliser pour autoriser un futur exécuteur commercial sans ajouter périmètre, montant, expiration et consommation unique.
Le moteur existant reste séquentiel et produit des brouillons/prototypes. Les KPI commerciaux doivent être saisis ou faire l'objet d'une future intégration approuvée.

## Respect de l'existant
Le paquet embarque l'archive source intacte et un patch limité. Les ressources métier originales sont préservées lors de la préparation sur le poste, sans réécriture. Les tests ici ont utilisé le repli des fiches de rôles ; celui-ci indique désormais explicitement l'identifiant du rôle. Pas de service externe connecté, modifié ou publié.

## Ajouts 1.3
Configuration locale des fournisseurs par projet, référence de secret sans exposition de sa valeur, édition des configurations. Aucun adaptateur distant ajouté. Rapport intégral des 30 derniers audits et export JSON. Sélecteur des modèles détectés. Tests supplémentaires : validation des URLs, références et projets, édition, absence de secret dans la réponse.

CORRECTIF 1.3.1 : lien Ouvrir l’aperçu dans un nouvel onglet pour tous les projets existants. Les liens Découvrir sont des ancres internes ; nouveaux libellés explicites pour les nouveaux prototypes. En-têtes des ressources d’aperçu adaptés au cadre isolé, sans retirer sandbox ni ouvrir les API. 66 tests Python et syntaxe JavaScript validés ; test visuel navigateur non effectué (exécutable absent). Ne pas régénérer une démonstration existante pour appliquer ce correctif : cela pourrait remplacer ses fichiers.
