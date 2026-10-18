# Analyse et plan de finalisation — Chelsea Coiffure

Audit du 19 septembre 2026.

## Conclusion

Le projet possède le socle d'un MVP de salon de coiffure : vitrine, catalogue, galerie, demandes de rendez-vous, espace de gestion et notifications. Il reste une phase de fiabilisation et de préparation à l'exploitation avant une ouverture aux clients. Une réécriture ne se justifie pas sur les éléments examinés.

Hypothèse de périmètre : un salon, une personne qui réalise les prestations, confirmation manuelle des demandes, sans paiement en ligne. Une équipe de plusieurs coiffeurs demanderait un modèle de ressources et un planning différents.

## Vérifications réalisées

- Lecture de l'architecture, modèles, vues, moteur de disponibilité, configuration, templates et tests.
- Suite existante : **19 tests réussis**.
- `manage.py check` : aucune anomalie signalée.
- `makemigrations --check --dry-run` : aucun changement de modèle sans migration.
- `check --deploy --settings=config.settings.production` : avertissement `security.W009` sur la robustesse de la clé secrète chargée localement. Cela ne renseigne pas sur une éventuelle configuration distante.
- Reproductions supplémentaires sur une base SQLite **en mémoire**, sans modifier les données métier locales ni envoyer de vrais courriels.
- Aucun dépôt Git détecté dans ce dossier. Aucun pipeline CI ni manifeste de déploiement trouvé dans les fichiers examinés.

Limites : pas de recette visuelle au navigateur, pas de test sur PostgreSQL, pas d'envoi réel Resend, pas de téléversement Cloudinary ni d'inspection d'un hébergement distant. Les tests verts ne prouvent donc pas la préparation à la production.

## Ce qui existe

| Domaine | État constaté |
|---|---|
| Site public | Accueil, catalogue filtré, fiches services, galerie et pages de politique présentes. |
| Réservation | Choix de prestation et de créneau, coordonnées, validation, honeypot, nonce de session, rendez-vous en attente. |
| Disponibilités | Horaires, jours fermés, périodes bloquées, durées et temps de préparation, fenêtre de réservation, vérification transactionnelle. |
| Gestion | Connexion staff, tableau de bord, listes, calendrier, statuts, notes, horaires, blocages et paramètres. |
| Catalogue et galerie | Consultation dans la gestion ; création et modification déléguées à l'administration Django. |
| Courriels | Templates et journal d'envoi ; intégration HTTP Resend et backend Django de repli. |
| Infrastructure | Réglages développement/production, configuration PostgreSQL et Cloudinary conditionnelle, protections Django. |

## Défauts prioritaires

### P0 — Intégrité du planning

**Reconfirmation créant un conflit, reproduite.** Dans `apps/accounts/views.py`, une action `confirm` change directement le statut sans revalider le créneau ni l'état précédent. Un rendez-vous annulé a pu être reconfirmé alors qu'un autre rendez-vous confirmé occupait exactement la même période : deux rendez-vous actifs obtenus.

À faire : centraliser les transitions autorisées, verrouiller et revalider toute réactivation, traiter aussi les accès par l'administration Django, et définir le comportement lors d'un blocage ou changement d'horaires qui touche des rendez-vous existants. Tester les courses concurrentes sur PostgreSQL ; les tests SQLite ne valident pas le verrouillage de production.

### P0 — Entrées invalides et erreurs serveur

**Trois erreurs 500 reproduites :** mois `13` avec un service valide sur `/reservation/`, identifiant de service `abc`, et fermeture avant ouverture dans `/gestion/horaires/`.

À faire : valider et borner dates, mois, années et identifiants ; utiliser des formulaires Django pour horaires, blocages et paramètres ; afficher les erreurs près des champs ; enregistrer un ensemble d'horaires de manière atomique. Les blocages et paramètres utilisent également directement les valeurs POST et doivent être couverts. Remplacer l'affichage brut des exceptions de réservation par un message public stable et une trace interne.

### P1 — Courriels et suivi client

**Adresse manquante, reproduite.** Les templates attendent `site_settings`, mais `EmailService` ne le fournit pas lors du rendu sans requête. Le courriel de confirmation ne contient pas l'adresse attendue.

Les vues de gestion annoncent aussi un courriel envoyé sans tenir compte du résultat booléen du service. L'envoi est synchrone, sans mécanisme de reprise identifié. Le repli SMTP n'est pas explicitement configuré dans les réglages examinés. Les templates `reminder` et `rescheduled` existent, mais aucun ordonnanceur de rappel ni parcours de déplacement n'a été trouvé.

À faire : fournir l'identité et l'adresse du salon, le bon fuseau horaire et des liens absolus utiles ; vérifier le résultat des envois ; rendre les échecs visibles et réessayables sans créer un second rendez-vous. Tester réellement les courriels client et salon en préproduction. Les rappels et déplacements peuvent être reportés après ouverture si une procédure manuelle est acceptée.

### P1 — Règles métier et cohérence

- Le texte par défaut annonce 24 heures de préavis, mais le réglage technique par défaut est de 2 heures.
- L'annulation ne vérifie ni délai ni date, et peut convertir un rendez-vous terminé ou refusé en annulation client.
- Le moteur utilise le fuseau configurable du salon, alors que plusieurs vues utilisent la date UTC de `timezone.now().date()` et les affichages le fuseau Django fixé à `Europe/Paris`.
- Les euros, Paris et plusieurs coordonnées sont présents par défaut ou codés en dur : confirmer le pays, la devise et le fuseau réels du salon.
- Le revenu « ce mois-ci » a une borne de début mais pas de fin : les rendez-vous des mois suivants peuvent entrer dans le total.
- Les recherches de conflits ajoutent des marges fixes différentes (2 ou 3 heures), alors que les buffers de service n'ont pas de borne métier correspondante. Harmoniser le calcul ou imposer des limites validées.
- L'adresse courriel des clients n'est pas unique alors que `get_or_create(email=...)` suppose implicitement une identité stable. Décider si une adresse peut représenter plusieurs clients et adapter le modèle et les accès.

### P1 — Préparation de production

- Remplacer la clé faible signalée et faire échouer le démarrage de production si un secret ou une configuration indispensable manque.
- Définir un déploiement reproductible : serveur applicatif (Gunicorn/Uvicorn évoqué mais absent des dépendances), PostgreSQL, fichiers statiques, médias persistants, domaine et terminaison HTTPS.
- Vérifier les en-têtes du proxy de confiance et CSRF sur le domaine final.
- Le limiteur utilise un cache mémoire par processus, des incréments non atomiques et fait confiance à `X-Forwarded-For`. Le rendre cohérent entre workers et ne faire confiance qu'au proxy maîtrisé.
- Versionner le code, figer les dépendances validées et automatiser tests et contrôles de migrations.
- Définir sauvegardes, restauration testée, traces d'erreurs, suivi des courriels et retour arrière.

### P2 — Finition du produit

- Remplacer les contenus et images de démonstration, vérifier les liens sociaux, les prix, durées et instructions.
- Décider si l'administration Django suffit pour gérer services et galerie au lancement. Vérifier les permissions du compte opérationnel ; être staff ne donne pas automatiquement toutes les permissions de l'administration.
- Vérifier le parcours mobile, clavier, erreurs de formulaire, contrastes et états vides au navigateur.
- Ajouter la pagination aux listes qui grandissent et mesurer les requêtes du calendrier mensuel avant optimisation.
- Corriger les métadonnées de partage (URLs d'images absolues), sérialiser correctement le JSON-LD et définir l'indexation des pages de réservation et de gestion.
- Adapter les textes de confidentialité au fonctionnement réel : ils disent actuellement qu'aucune donnée n'est transmise à des tiers, alors que l'intégration de courriels prévoit Resend. Définir aussi la conservation et la procédure de suppression. Ce constat porte sur la cohérence du produit, pas sur une validation juridique.

## Plan d'exécution

Ordre conseillé : cadrage → fiabilité métier → notifications et gestion → préproduction → recette → ouverture.

| Étape | Livrables | Critère de sortie | Charge indicative |
|---|---|---|---|
| 1. Cadrer et sécuriser le travail | Périmètre MVP, identité du salon, règles de délai et d'annulation, dépôt Git et sauvegarde initiale | Règles écrites et code récupérable | 0,5–1 jour |
| 2. Corriger le planning et les formulaires | Transitions centralisées, validations, écritures atomiques, fuseau cohérent, tests de régression | Aucun conflit sur réactivation ; entrées invalides traitées sans 500 ; concurrence vérifiée sur PostgreSQL | 2–3 jours |
| 3. Fiabiliser les courriels et la gestion | Contenu complet, liens, visibilité des échecs et reprise ; indicateurs corrigés ; permissions vérifiées | Une réservation, confirmation et annulation produisent les bons états et courriels ; panne d'envoi observable et récupérable | 1–2 jours |
| 4. Préparer la préproduction | Configuration reproductible, secrets, PostgreSQL, médias, statiques, HTTPS, CI, sauvegardes et supervision | Installation depuis un environnement vierge ; restauration et retour arrière éprouvés | 1–2 jours |
| 5. Finaliser le contenu et faire la recette | Vrais services et photos, textes cohérents, recette mobile et bureau, corrections UX | Chelsea réalise seule les opérations quotidiennes ; aucun défaut bloquant ouvert | 1–2 jours |
| 6. Ouvrir | Domaine final, paramètres réels, données prêtes, vérification d'une réservation réelle encadrée | Parcours client et salon validés sur le domaine final | 0,5 jour |

Estimation : **6 à 10,5 jours de travail effectif**, pour une personne connaissant Django, dans le périmètre décrit. Ce n'est pas un engagement de délai : disponibilité des contenus, accès aux services, choix d'hébergement et découverte de défauts pendant la recette peuvent allonger le calendrier.

## Conditions d'ouverture

- [ ] Aucun double rendez-vous possible dans les parcours supportés, y compris gestion et administration.
- [ ] Réservation, refus, confirmation et annulation validés de bout en bout.
- [ ] Formulaires invalides gérés sans erreur serveur ni enregistrement partiel.
- [ ] Horaires, fuseau, devise et règles affichées conformes aux règles réellement appliquées.
- [ ] Courriels reçus sur de vraies boîtes de test ; échecs visibles et réessayables.
- [ ] Catalogue, photos, coordonnées et politiques validés par le salon.
- [ ] Utilisation mobile et permissions du compte salon vérifiées.
- [ ] Production configurée, vérifications Django satisfaisantes, statiques et médias accessibles.
- [ ] Sauvegarde restaurée avec succès et procédure de retour arrière documentée.
- [ ] Tests exécutés automatiquement et aucune anomalie bloquante restante.

## Décisions à prendre pour lancer l'exécution

1. Pays, devise, fuseau, adresse et nom commercial définitif.
2. Une seule coiffeuse ou plusieurs personnes réservables ?
3. Préavis minimal et règle d'annulation réellement souhaités.
4. Rappels automatiques et déplacement de rendez-vous indispensables à l'ouverture, ou phase suivante ?
5. Hébergement, domaine et comptes Resend/Cloudinary existants ou à préparer.

La priorité immédiate est l'étape 2, après sauvegarde et versionnement : corriger les erreurs reproduites et protéger l'intégrité du planning avant d'ajouter des fonctionnalités.
