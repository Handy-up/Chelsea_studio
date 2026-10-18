from django.core.exceptions import ValidationError
from apps.bookings.configurator_views import get_configuration, SESSION_KEY
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from django.utils.crypto import get_random_string
from apps.services.models import Service
from apps.bookings.models import Appointment
from apps.bookings.forms import BookingCustomerForm
from apps.bookings.services.availability import AvailabilityService, SlotUnavailableError
from apps.core.rate_limit import is_rate_limited
from apps.core.calendar_utils import build_month_grid, adjacent_months, month_label
from apps.notifications.services.email_service import EmailService

BOOKING_NONCE_SESSION_KEY = 'booking_nonce'


def get_or_create_booking_nonce(request):
    nonce = request.session.get(BOOKING_NONCE_SESSION_KEY)
    if not nonce:
        nonce = get_random_string(32)
        request.session[BOOKING_NONCE_SESSION_KEY] = nonce
    return nonce


def build_booking_calendar_context(request, service, today):
    """
    Construit le contexte du calendrier mensuel de réservation (vert = disponible,
    rouge = complet/fermé) pour le service sélectionné, en tenant compte de la
    navigation mois précédent/suivant demandée en GET.
    """
    try:
        year = int(request.GET.get('year') or today.year)
        month = int(request.GET.get('month') or today.month)
        if not 1 <= month <= 12 or not today.year <= year <= today.year + 1:
            raise ValueError()
    except (TypeError, ValueError):
        year, month = today.year, today.month

    _, max_booking_dt = AvailabilityService.get_booking_window()

    weeks = None
    if service:
        def day_status(a_date):
            return 'available' if AvailabilityService.has_availability(service, a_date) else 'unavailable'
        weeks = build_month_grid(year, month, day_status, today=today)

    (prev_year, prev_month), (next_year, next_month) = adjacent_months(year, month)

    return {
        'calendar_weeks': weeks,
        'calendar_month_label': month_label(year, month),
        'calendar_year': year,
        'calendar_month': month,
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'can_go_prev': (year, month) > (today.year, today.month),
        'can_go_next': (year, month) < (max_booking_dt.year, max_booking_dt.month),
    }


def booking_wizard_view(request):
    """
    Vue principale du tunnel de réservation étape par étape.
    """
    selected_service_id = request.GET.get('service') or request.POST.get('service_id')
    selected_date_str = request.GET.get('date') or request.POST.get('date')
    selected_slot = request.GET.get('slot') or request.POST.get('slot')

    services = Service.objects.filter(is_active=True).select_related('category')
    selected_service = None
    if selected_service_id and str(selected_service_id).isdigit():
        selected_service = services.filter(pk=selected_service_id).first()

    today = timezone.localtime(timezone.now(), AvailabilityService.get_business_timezone()).date()
    configured = None
    configuration_error = ''
    if request.POST.get('configuration_token'):
        try:
            configured = get_configuration(request, final=True)
            selected_service = configured.service
        except ValidationError as error:
            configuration_error = ' '.join(error.messages)
    calendar_context = build_booking_calendar_context(request, configured, today)

    available_slots = []
    if configured and selected_date_str:
        try:
            available_slots = AvailabilityService.get_available_slots(configured, selected_date_str)
        except Exception:
            available_slots = []

    form = BookingCustomerForm(request.POST or None)
    booking_nonce = get_or_create_booking_nonce(request)

    if request.method == 'POST' and request.POST.get('action') == 'submit_booking':
        posted_nonce = request.POST.get('booking_nonce', '')
        if is_rate_limited(request, 'booking', getattr(settings, 'BOOKING_RATE_LIMIT_PER_HOUR', 8)):
            messages.error(request, "Trop de demandes de réservation ont été envoyées depuis cet appareil. Merci de réessayer plus tard.")
        elif not posted_nonce or posted_nonce != request.session.get(BOOKING_NONCE_SESSION_KEY):
            messages.error(request, "Ce formulaire a déjà été envoyé ou a expiré. Merci de réessayer.")
            request.session[BOOKING_NONCE_SESSION_KEY] = get_random_string(32)
            booking_nonce = request.session[BOOKING_NONCE_SESSION_KEY]
        elif not configured:
            messages.error(request, configuration_error or 'Veuillez configurer et confirmer votre soin.')
        elif not selected_service:
            messages.error(request, "Veuillez sélectionner un service.")
        elif not selected_slot:
            messages.error(request, "Veuillez choisir un créneau horaire.")
        elif form.is_valid():
            try:
                # Appeler le moteur de réservation transactionnel
                appointment = AvailabilityService.book_appointment(
                    customer_data=form.cleaned_data,
                    service=selected_service,
                    starts_at_dt=selected_slot,
                    client_note=form.cleaned_data.get('client_note', ''),
                    configuration=configured.snapshot, files=request.FILES
                )

                # Envoyer les notifications par email
                EmailService.send_notification(appointment, 'confirmation_request')
                EmailService.send_notification(appointment, 'new_appointment_admin')

                request.session.pop(BOOKING_NONCE_SESSION_KEY, None)
                request.session.pop(SESSION_KEY, None)
                return redirect('bookings:confirmation', public_id=appointment.public_id)

            except (SlotUnavailableError, ValidationError) as err:
                messages.error(request, str(err))
            except Exception as e:
                messages.error(request, "La réservation n’a pas pu être enregistrée. Merci de réessayer.")

    context = {
        'personalization_preview': settings.DEBUG and request.GET.get('apercu') == 'personnalisation',
        'show_personalization_preview_link': settings.DEBUG,
        'configurator_initial': {
            'preselectedId': str(selected_service.pk) if selected_service else '',
            'selection': request.session.get(SESSION_KEY, {}).get('selection') if request.method == 'POST' else None,
            'token': request.POST.get('configuration_token', '') if configured and not request.FILES else '',
            'step': 4 if configured and not request.FILES else 1,
            'date': selected_date_str or '', 'slot': selected_slot or '',
            'fileReselect': bool(request.FILES),
        },
        'slots': available_slots,
        'services': services,
        'selected_service': selected_service,
        'selected_date_str': selected_date_str,
        'selected_slot': selected_slot,
        'available_slots': available_slots,
        'form': form,
        'booking_nonce': booking_nonce,
        'meta_title': "Prendre Rendez-vous - Chelsea Coiffure",
        'meta_description': "Réservez votre créneau coiffure avec Chelsea en quelques clics.",
        **calendar_context,
    }
    return render(request, 'bookings/booking_wizard.html', context)


def availability_calendar_view(request):
    """
    Endpoint HTMX qui régénère le calendrier mensuel (navigation mois précédent/suivant)
    pour le service sélectionné dans le tunnel de réservation.
    """
    try:
        service = get_configuration(request)
    except ValidationError as error:
        return render(request, 'bookings/partials/calendar.html', {'configuration_error': ' '.join(error.messages)}, status=400)
    today = timezone.localtime(timezone.now(), AvailabilityService.get_business_timezone()).date()
    context = {
        'selected_service': service,
        **build_booking_calendar_context(request, service, today),
    }
    return render(request, 'bookings/partials/calendar.html', context)


def availability_api_view(request):
    """
    Endpoint HTMX pour mettre à jour la liste des créneaux en fonction de la date et du service.
    """
    date_str = request.GET.get('date')
    try:
        service = get_configuration(request)
    except ValidationError as error:
        return render(request, 'bookings/partials/slots_list.html', {'error': ' '.join(error.messages)}, status=400)

    try:
        slots = AvailabilityService.get_available_slots(service, date_str)
    except Exception as e:
        slots = []

    context = {
        'slots': slots,
        'service': service,
        'date_str': date_str,
    }
    return render(request, 'bookings/partials/slots_list.html', context)


def booking_confirmation_view(request, public_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related('customer', 'service'),
        public_id=public_id
    )
    context = {
        'appointment': appointment,
        'meta_title': "Confirmation de Réservation - Chelsea Coiffure",
    }
    return render(request, 'bookings/confirmation.html', context)


def cancel_appointment_view(request, public_id, token):
    appointment = get_object_or_404(Appointment, public_id=public_id, confirmation_token=token)

    if request.method == 'POST':
        if appointment.status in ['cancelled_by_customer', 'cancelled_by_admin']:
            messages.info(request, "Ce rendez-vous a déjà été annulé.")
        else:
            appointment.status = 'cancelled_by_customer'
            appointment.save()
            EmailService.send_notification(appointment, 'cancelled')
            messages.success(request, "Votre rendez-vous a été annulé avec succès.")
            return redirect('core:home')

    return render(request, 'bookings/cancel.html', {'appointment': appointment})
