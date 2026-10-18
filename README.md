# Chelsea Studio Coiffure

Application Django mobile-first de présentation, catalogue de services et demande de rendez-vous pour Chelsea.

## Stack

- Python 3.14
- Django 6
- Django Templates
- ORM Django
- PostgreSQL en production, SQLite en développement local
- HTMX et Alpine.js servis depuis `static/js/`
- Cloudinary pour les médias en production
- Resend pour les courriels transactionnels
- pytest et pytest-django

## Installation locale

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py createsuperuser
python manage.py runserver
```

Le site public est disponible sur `http://127.0.0.1:8000/`.
L'espace privé est disponible sur `http://127.0.0.1:8000/gestion/`.

## Variables d'environnement

Les valeurs attendues sont documentées dans `.env.example`.

Variables principales :

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `DB_ENGINE`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`
- `RESEND_API_KEY`
- `DEFAULT_FROM_EMAIL`
- `ADMIN_EMAIL`
- `BOOKING_MIN_NOTICE_HOURS`
- `BOOKING_MAX_DAYS_AHEAD`
- `BOOKING_RATE_LIMIT_PER_HOUR`
- `LOGIN_RATE_LIMIT_PER_HOUR`

## Données de démonstration

```bash
python manage.py seed_demo
```

Pour repartir d'une base métier vide avant de recréer la démo :

```bash
python manage.py seed_demo --reset
```

La démo crée le profil de Chelsea, les liens sociaux fictifs, les catégories Hommes/Femmes, six services, les horaires hebdomadaires, une galerie placeholder et quelques rendez-vous futurs.

## Tests

```bash
pytest
```

La suite couvre les disponibilités, jours fermés, blocages, chevauchements, buffers, double soumission, création client, annulation, permissions, connexion privée, formulaires, courriels, URLs publiques, pages légales, filtres de services et commande de démo.

## Architecture

Applications Django :

- `apps.core` : paramètres singleton, pages publiques, contexte global, commande de démo.
- `apps.accounts` : espace privé `/gestion/` et connexion Chelsea.
- `apps.services` : catégories, services et images de services.
- `apps.gallery` : galerie des réalisations.
- `apps.bookings` : clients, horaires, blocages, rendez-vous, disponibilité transactionnelle.
- `apps.notifications` : abstraction d'envoi courriel et journalisation.

Réglages :

- `config/settings/base.py`
- `config/settings/development.py`
- `config/settings/production.py`

## Production

1. Créer une base PostgreSQL.
2. Renseigner `.env` avec `DB_ENGINE=postgres`, les identifiants DB, `SECRET_KEY`, `ALLOWED_HOSTS`, les clés Cloudinary et Resend.
3. Définir `DJANGO_SETTINGS_MODULE=config.settings.production`.
4. Installer les dépendances avec `pip install -r requirements.txt`.
5. Exécuter `python manage.py migrate`.
6. Exécuter `python manage.py collectstatic`.
7. Créer le compte Chelsea avec `python manage.py createsuperuser`.
8. Servir l'application via Gunicorn/Uvicorn derrière HTTPS.

Les réglages de production activent HTTPS forcé, cookies sécurisés, SameSite, HSTS, protection clickjacking et headers de sécurité Django.
