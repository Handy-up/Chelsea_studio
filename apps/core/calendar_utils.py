"""
Utilitaire générique de construction de grille calendrier mensuelle.

Partagé entre le tunnel de réservation public (apps.bookings) et l'agenda
de gestion privé (apps.accounts) afin d'éviter deux implémentations
dupliquées d'un même calcul de grille de semaines.
"""
import calendar
from datetime import date


def build_month_grid(year, month, day_status_fn, today=None):
    """
    Construit une grille de semaines (Lundi -> Dimanche) pour le mois donné.

    `day_status_fn(a_date) -> 'available' | 'unavailable' | None` détermine le
    statut visuel (pastille verte / rouge / aucune) d'un jour du mois affiché.
    Les jours hors mois ou passés ne sont jamais interrogés.

    Retourne une liste de semaines, chaque semaine étant une liste de dicts :
    {'date', 'day', 'in_month', 'is_today', 'is_past', 'status'}
    """
    cal = calendar.Calendar(firstweekday=0)
    today = today or date.today()
    weeks = []
    for week in cal.monthdatescalendar(year, month):
        days = []
        for day_date in week:
            in_month = day_date.month == month
            is_past = day_date < today
            status = day_status_fn(day_date) if (in_month and not is_past) else None
            days.append({
                'date': day_date,
                'day': day_date.day,
                'in_month': in_month,
                'is_today': day_date == today,
                'is_past': is_past,
                'status': status,
            })
        weeks.append(days)
    return weeks


def adjacent_months(year, month):
    """Retourne ((année_préc, mois_préc), (année_suiv, mois_suiv)) pour la navigation."""
    prev_month, prev_year = month - 1, year
    if prev_month == 0:
        prev_month, prev_year = 12, year - 1

    next_month, next_year = month + 1, year
    if next_month == 13:
        next_month, next_year = 1, year + 1

    return (prev_year, prev_month), (next_year, next_month)


MONTH_LABELS_FR = [
    '', 'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
    'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre',
]


def month_label(year, month):
    return f"{MONTH_LABELS_FR[month]} {year}"
