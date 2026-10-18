# Configurateur de réservation

## Parcours livré

L’étape Soin propose le type de client, une catégorie de coiffure, un style si la catégorie en possède, puis ses options. Le bouton Continuer affiche le récapitulatif ; Choisir une date valide la sélection sur le serveur avant d’ouvrir le calendrier existant. Date, Heure et Infos sont conservées. Le calendrier utilise la durée configurée, y compris les ajustements.

Le résumé reste fixé en bas sur mobile et dans une colonne à droite à partir de 900 px. Les choix utilisent des boutons accessibles ou des champs natifs, avec indication de sélection, focus visible et options obligatoires. Le chargement initial du catalogue couvre simultanément catégories et options ; un squelette, des états vides et une action d’actualisation gèrent les erreurs.

## Correspondance avec les modèles existants

- `Service` représente une catégorie de coiffure réservable (`HairstyleCategory` dans le brief). Il conserve ses images, sa durée et son prix de base. Aucun renommage destructif ni deuxième catalogue parallèle.
- `ServiceCategory` reste le regroupement historique des pages publiques.
- `ClientType` fournit les types de clients de la nouvelle UI ; la relation `Service.client_types` filtre les prestations. Une relation vide signifie tous les types actifs.
- `HairstyleSubcategory` fournit les styles d’une prestation, avec image et ajustements facultatifs de prix et durée.
- `HairstyleOptionGroup` définit le nom, la description, le type de champ, le caractère obligatoire et l’ordre. Son slug sert de clé éditoriale ; les échanges utilisent son ID.
- `HairstyleOptionValue` définit les valeurs possibles et leurs ajustements.
- `HairstyleOptionAssignment` affecte un groupe à UNE prestation OU UN style. Une affectation au style remplace celle de la prestation pour le même groupe, sans double comptage. Le caractère obligatoire peut être hérité ou remplacé.

La migration `services.0004` crée les types de clients à partir des regroupements déjà présents en base et relie leurs prestations. Sur une base neuve, les créer dans l’administration, ou utiliser la commande de démo existante en développement. Aucune coiffure ni option métier n’est définie en dur dans le frontend.

## Administrer les options

Dans `/admin/` :

1. Créer les types de clients et régler leur ordre/activation.
2. Sur une prestation, sélectionner ses types de clients, son prix, sa durée et son image habituels.
3. Facultativement créer des styles (`HairstyleSubcategory`) rattachés à la prestation. Si des styles actifs existent, le client doit en choisir un. Sans style, la section est masquée.
4. Créer un groupe d’options et ses valeurs dans les lignes intégrées au formulaire.
5. Affecter le groupe à une prestation ou un style avec `HairstyleOptionAssignment`.

Types pris en charge : `single_select`, `multi_select`, `boolean`, `text`, `textarea`, `number`, `photo`, `file`.

Pour `boolean`, les valeurs techniques `true` et `false` permettent d’associer un supplément à Oui et/ou Non. Sans valeur correspondante, aucun supplément n’est appliqué. Un Non explicite satisfait une réponse obligatoire. Les champs texte et nombre collectent des informations : ils ne multiplient pas implicitement un prix. Les suppléments sont liés aux valeurs sélectionnables, jamais au libellé affiché.

Prix fixe, « à partir de », devis et ajustements positifs/négatifs sont pris en charge. La devise EUR existante est conservée : les exemples en dollars du brief ne changent pas la devise commerciale du salon.

## Fichiers et validation

Les fichiers restent dans le formulaire pendant la configuration. La validation intermédiaire vérifie leur contenu mais ne les stocke pas. Ils sont enregistrés avec le rendez-vous final, dans `AppointmentAttachment`, sans URL publique. Un lien de téléchargement protégé pour le personnel apparaît dans la fiche de gestion.

Formats : JPEG, PNG, WebP ; PDF également pour un champ document. Limites : 5 Mo par fichier, 20 Mo cumulés. Le contenu d’une image est vérifié avec Pillow ; les documents doivent avoir une signature PDF. Les téléchargements sont forcés en pièce jointe, avec `nosniff` et sans cache public. Ce contrôle ne remplace pas une éventuelle analyse antivirus de production. Les fichiers binaires sont stockés en base pour éviter une exposition par le stockage public des images du catalogue ; prévoir l’évolution vers un stockage privé si le volume le justifie.

Après une erreur de formulaire impliquant des fichiers, les autres choix et coordonnées sont conservés, mais le navigateur impose une nouvelle sélection des fichiers. Un message explique cette étape.

## Source de vérité

- `GET /reservation/catalogue/` : catalogue actif de la base, aucun mock.
- `POST /reservation/configurer/` : IDs, valeurs saisies et fichiers ; validation et calcul serveur, puis émission d’un identifiant opaque lié à la session, valable deux heures.
- Le calendrier et les créneaux demandent cet identifiant. Ils ne calculent pas les options eux-mêmes.
- La création finale revalide la configuration dans la transaction de réservation et recalcule le prix et la durée depuis la base. Les montants provenant du navigateur ne sont jamais utilisés.
- Un changement du catalogue depuis la confirmation invalide la sélection au lieu d’accepter silencieusement un nouveau prix.
- Un instantané des noms, valeurs et totaux est sauvegardé sur le rendez-vous ; `ends_at` reflète la durée réelle. La gestion, la confirmation publique et les notifications initiales reprennent ces informations.

Une configuration active par session est utilisée. Confirmer un autre soin dans un second onglet invalide l’ancien identifiant ; il faut alors reconfirmer le premier soin.

## Organisation du code

- `apps/services/services/configuration.py` : catalogue, validation, calculs purs et représentation d’une prestation configurée.
- `apps/bookings/configurator_views.py` : API et téléchargement privé.
- `apps/bookings/services/availability.py` : durée effective et enregistrement transactionnel du rendez-vous configuré.
- `static/js/booking/engine.js` : fonctions pures de prix, durée, validation et transitions de sélection.
- `static/js/booking/configurator.js` : état Alpine, actions et échanges HTTP.
- `static/js/booking/types.d.ts` : contrats TypeScript des données ; l’application reste en JavaScript sans nouveau build React/TypeScript.
- `templates/bookings/configurator/` : composants séparés de sélection, options, récapitulatif et résumé.
- `static/css/configurator.css` : styles dédiés reprenant les variables du design existant.

## Validation effectuée

```sh
.venv/bin/python -m pytest -q
node --test tests/test_configurator_engine.cjs
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
```

38 tests Python et 7 tests JavaScript réussis, contrôles Django et migrations cohérents. Couverture : calculs décimaux, durée, groupes requis, false/0, options périmées, styles, changement de catégorie et style, prix falsifié, jeton lié à la session, fichiers invalides/manquants et accès privé, reprise après erreur, disponibilité et création avec durée majorée.

Recette navigateur : mobile 390 px, ordinateur 1280 px, progression jusqu’aux coordonnées, préselection depuis le catalogue, catégorie sans style, style avec les huit types de champs, recalcul 72 € / 75 min → 102 € / 120 min, récapitulatif et aperçu photo. Les données supplémentaires de recette et le serveur sur le port 8001 utilisent exclusivement une base temporaire séparée.

Migrations appliquées à la base locale, précédées d’une sauvegarde SQLite dans `/private/tmp/shelsea-before-configurator-20260929.sqlite3`. Aucun catalogue d’options commerciales n’a été inventé ni ajouté aux données réelles : les vrais styles, groupes et suppléments restent à renseigner dans l’administration.
