import json
import time
import uuid
from django.core.exceptions import ValidationError
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404
from apps.services.services.configuration import catalogue, resolve_configuration
from apps.bookings.models import AppointmentAttachment

SESSION_KEY = 'service_configuration'


def get_configuration(request, final=False):
    token = request.POST.get('configuration_token') or request.GET.get('configuration_token')
    saved = request.session.get(SESSION_KEY)
    if not saved or not token or saved['token'] != token or time.time() - saved['created'] > 7200:
        raise ValidationError('Veuillez confirmer votre soin avant de choisir une date (configuration valable 2 heures).')
    quote = resolve_configuration(saved['selection'], request.FILES, require_uploads=final)
    if quote.snapshot != saved['selection']:
        raise ValidationError('Le soin a été modifié par le salon. Vérifiez à nouveau votre sélection.')
    return quote


@require_GET
def catalogue_view(request):
    response = JsonResponse(catalogue())
    response['Cache-Control'] = 'no-store'
    return response


@require_POST
def configure_view(request):
    try:
        quote = resolve_configuration(json.loads(request.POST.get('selection', '{}')), request.FILES, require_uploads=True)
    except (ValidationError, ValueError, TypeError) as error:
        return JsonResponse({'error': ' '.join(error.messages) if isinstance(error, ValidationError) else 'Configuration invalide.'}, status=400)
    token = uuid.uuid4().hex
    request.session[SESSION_KEY] = {'token': token, 'selection': quote.snapshot, 'created': time.time()}
    return JsonResponse({'token': token, 'selection': quote.snapshot})


@staff_member_required
@require_GET
def attachment_view(request, pk):
    attachment = get_object_or_404(AppointmentAttachment, pk=pk)
    from django.utils.http import content_disposition_header
    response = HttpResponse(bytes(attachment.content), content_type=attachment.content_type)
    response['Content-Disposition'] = content_disposition_header(True, attachment.name)
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response
