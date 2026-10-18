"""Database-driven catalogue and authoritative booking quote calculation."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from io import BytesIO
from PIL import Image
from django.core.exceptions import ValidationError
from django.db.models import Q
from apps.services.models import Service, ClientType, HairstyleOptionAssignment


def calculate_service_price(base_price, selected_options):
    return (Decimal(str(base_price)) + sum((Decimal(str(v['priceAdjustment'])) for v in selected_options), Decimal(0))).quantize(Decimal('0.01'))


def calculate_service_duration(base_duration, selected_options):
    return base_duration + sum(v['durationAdjustmentMinutes'] for v in selected_options)


def adjustment(value):
    return {'priceAdjustment': str(value.price_adjustment), 'durationAdjustmentMinutes': value.duration_adjustment_minutes}


def applicable_groups(service, style=None):
    assignments = HairstyleOptionAssignment.objects.filter(
        Q(category=service) | (Q(subcategory=style) if style else Q(pk__in=[])),
        option_group__is_active=True,
    ).select_related('option_group').prefetch_related('option_group__values')
    # A style assignment explicitly overrides its inherited category assignment.
    result = {}
    for assignment in sorted(assignments, key=lambda a: (bool(a.subcategory_id), a.sort_order, a.pk)):
        group = assignment.option_group
        result[group.pk] = (group, group.is_required if assignment.is_required is None else assignment.is_required)
    return list(result.values())


def catalogue():
    def entity(obj):
        return {'id': str(obj.pk), 'name': obj.name, 'description': obj.description}
    def groups(service, style=None):
        return [{**entity(g), 'inputType': g.input_type, 'required': required,
                 'values': [{'id': str(v.pk), 'label': v.label, 'value': v.value, 'description': v.description,
                             'imageUrl': v.image.url if v.image else '', **adjustment(v)}
                            for v in g.values.all() if v.is_active]}
                for g, required in applicable_groups(service, style)]
    categories = []
    for service in Service.objects.filter(is_active=True).filter(Q(category__isnull=True) | Q(category__is_active=True)).prefetch_related('client_types', 'subcategories', 'images'):
        categories.append({'id': str(service.pk), 'name': service.name, 'description': service.short_description,
                           'imageUrl': service.get_cover_image_url(), 'basePrice': str(service.price),
                           'priceType': service.price_type, 'baseDurationMinutes': service.duration_minutes,
                           'clientTypeIds': [str(c.pk) for c in service.client_types.all()],
                           'groups': groups(service), 'subcategories': [
                               {**entity(style), 'imageUrl': style.image.url if style.image else '',
                                **adjustment(style), 'groups': groups(service, style)}
                               for style in service.subcategories.all() if style.is_active]})
    return {'clientTypes': [entity(c) for c in ClientType.objects.filter(is_active=True)], 'categories': categories}


def validate_upload(upload, kind):
    if upload.size > 5 * 1024 * 1024:
        raise ValidationError('Chaque fichier doit faire au maximum 5 Mo.')
    content = upload.read()
    upload.seek(0)
    if kind == 'file' and content.startswith(b'%PDF-'):
        return 'application/pdf'
    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
            if image.format not in ('JPEG', 'PNG', 'WEBP'):
                raise ValueError()
            return Image.MIME[image.format]
    except Exception:
        raise ValidationError('Ajoutez une image JPEG, PNG ou WebP, ou un PDF pour un document.')


@dataclass
class ConfiguredService:
    service: Service
    price: Decimal
    duration_minutes: int
    snapshot: dict
    uploads: list

    def __getattr__(self, key):
        return getattr(self.service, key)


def resolve_configuration(selection, files=None, require_uploads=False):
    if not isinstance(selection, dict):
        raise ValidationError('Configuration invalide.')
    try:
        service = Service.objects.get(pk=selection.get('categoryId'), is_active=True)
        client = ClientType.objects.get(pk=selection.get('clientTypeId'), is_active=True)
    except (Service.DoesNotExist, ClientType.DoesNotExist, ValueError, TypeError):
        raise ValidationError('Choisissez un type de client et une coiffure disponibles.')
    if service.category and not service.category.is_active:
        raise ValidationError('Cette coiffure n’est plus disponible.')
    if service.client_types.exists() and not service.client_types.filter(pk=client.pk).exists():
        raise ValidationError('Cette coiffure ne correspond pas au type de client.')
    style_id = selection.get('subcategoryId')
    styles = service.subcategories.filter(is_active=True)
    style = None
    if styles.exists() or style_id:
        try:
            style = styles.get(pk=style_id)
        except (ValueError, TypeError, styles.model.DoesNotExist):
            raise ValidationError('Choisissez un style disponible pour cette coiffure.')
    groups = applicable_groups(service, style)
    options = selection.get('selectedOptions', {})
    if not isinstance(options, dict) or set(options) - {str(g.pk) for g, _ in groups}:
        raise ValidationError('Une option ne correspond plus à votre sélection.')
    normalized, rows, adjustments, uploads = {}, [], [adjustment(style)] if style else [], []
    files = files or {}
    if sum(upload.size for upload in files.values()) > 20 * 1024 * 1024:
        raise ValidationError('Les pièces jointes doivent faire au maximum 20 Mo au total.')
    for group, required in groups:
        key, kind = str(group.pk), group.input_type
        value = options.get(key)
        label = ''
        if kind in ('single_select', 'multi_select', 'boolean'):
            if kind == 'boolean':
                if value is not None and not isinstance(value, bool):
                    raise ValidationError(f'{group.name} : choisissez Oui ou Non.')
                ids = []
                if value is not None:
                    matches = list(group.values.filter(is_active=True, value='true' if value else 'false'))
                    if len(matches) > 1:
                        raise ValidationError('Configuration du groupe invalide.')
                    ids = [str(v.pk) for v in matches]
                label = 'Oui' if value else 'Non'
            else:
                ids = value if kind == 'multi_select' else ([] if value in (None, '') else [value])
                if ids is None:
                    ids = []
                if not isinstance(ids, list) or any(not isinstance(v, str) or not v.isdigit() for v in ids) or len(ids) != len(set(ids)):
                    raise ValidationError(f'{group.name} : choix invalide.')
            values = list(group.values.filter(pk__in=ids, is_active=True))
            if len(values) != len(ids):
                raise ValidationError(f'{group.name} : option indisponible.')
            adjustments.extend(adjustment(v) for v in values)
            if kind != 'boolean':
                label = ', '.join(v.label for v in values)
        elif kind in ('photo', 'file'):
            upload = files.get(f'option_file_{key}')
            if upload:
                mime = validate_upload(upload, kind)
                value = {'name': upload.name[:255]}
                uploads.append((group.pk, upload, mime))
            elif require_uploads:
                value = None
            elif value is not None and (not isinstance(value, dict) or not isinstance(value.get('name'), str)):
                raise ValidationError('Fichier invalide.')
            label = value.get('name', '') if isinstance(value, dict) else ''
        elif kind == 'number':
            if value not in (None, ''):
                try:
                    number = Decimal(str(value))
                    if isinstance(value, bool) or not number.is_finite() or abs(number) > 1000000:
                        raise InvalidOperation()
                    value = float(number)
                except (InvalidOperation, ValueError):
                    raise ValidationError(f'{group.name} : nombre invalide.')
            label = str(value) if value not in (None, '') else ''
        else:
            if value is not None and (not isinstance(value, str) or len(value) > 2000):
                raise ValidationError(f'{group.name} : texte invalide (2 000 caractères maximum).')
            value = value.strip() if value else ''
            label = value
        empty = value is None or value == '' or value == [] or value == {}
        if required and empty:
            raise ValidationError(f'Complétez « {group.name} ».')
        if not empty:
            normalized[key] = value
            rows.append({'group': group.name, 'value': label})
    price = calculate_service_price(service.price, adjustments)
    duration = calculate_service_duration(service.duration_minutes, adjustments)
    if price < 0 or price > Decimal('999999.99') or duration <= 0 or duration > 1440:
        raise ValidationError('Cette combinaison ne peut pas être réservée. Contactez le salon.')
    snapshot = {'clientTypeId': str(client.pk), 'clientTypeName': client.name,
                'categoryId': str(service.pk), 'categoryName': service.name,
                'subcategoryId': str(style.pk) if style else None, 'subcategoryName': style.name if style else '',
                'selectedOptions': normalized, 'options': rows, 'calculatedPrice': str(price),
                'calculatedDurationMinutes': duration, 'priceType': service.price_type}
    return ConfiguredService(service, price, duration, snapshot, uploads)
