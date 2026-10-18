"""
Bibliothèque de composants d'interface réutilisables pour Chelsea Coiffure.

Objectif : éliminer la duplication de markup (badges de statut, lignes de
liste, cartes de métriques, en-têtes de page, états vides) qui était
auparavant recopiée avec des styles inline dans une dizaine de templates.

Chaque tag `inclusion_tag` restitue un petit fragment HTML cohérent avec le
design system défini dans `static/css/main.css`.
"""
from django import template

register = template.Library()


@register.inclusion_tag('_components/status_badge.html')
def status_badge(status, label):
    """Affiche un badge coloré représentant le statut d'un rendez-vous ou d'un élément."""
    return {'status': status, 'label': label}


@register.inclusion_tag('_components/list_row.html')
def list_row(title, meta='', url='', status='', status_label=''):
    """Ligne de liste standard (titre + méta + badge optionnel), utilisée pour les rendez-vous, services, etc."""
    return {
        'title': title,
        'meta': meta,
        'url': url,
        'status': status,
        'status_label': status_label,
    }


@register.inclusion_tag('_components/metric_card.html')
def metric_card(label, value):
    """Petite carte chiffre-clé pour le tableau de bord."""
    return {'label': label, 'value': value}


@register.inclusion_tag('_components/empty_state.html')
def empty_state(text, card=False):
    """Message d'état vide cohérent (aucun résultat, aucune donnée, etc.)."""
    return {'text': text, 'card': card}


@register.inclusion_tag('_components/page_header.html')
def page_header(title, subtitle=''):
    """En-tête de page standard (titre + sous-titre optionnel)."""
    return {'title': title, 'subtitle': subtitle}
