from datetime import datetime, date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone
from apps.core.rate_limit import is_rate_limited
from apps.core.calendar_utils import build_month_grid, adjacent_months, month_label
from apps.bookings.models import Appointment, BusinessHours, BlockedPeriod, Customer
from apps.services.models import Service, ServiceCategory, ServiceImage
from apps.gallery.models import GalleryItem
from apps.core.models import SiteSettings
from apps.notifications.services.email_service import EmailService

def is_chelsea(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def appointment_row(appointment, title, meta):
    """
    Prépare les données d'affichage d'un rendez-vous pour le composant `{% list_row %}`.
    Centralise le formatage (autrement dupliqué dans 4 templates gestion différents).
    """
    return {
        'title': title,
        'meta': meta,
        'url': reverse('accounts:gestion_appointment_detail', args=[appointment.public_id]),
        'status': appointment.status,
        'status_label': appointment.get_status_display(),
    }

class ChelseaLoginView(LoginView):
    template_name = 'gestion/login.html'
    redirect_authenticated_user = True

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST' and is_rate_limited(
            request,
            'gestion-login',
            getattr(settings, 'LOGIN_RATE_LIMIT_PER_HOUR', 12),
        ):
            return HttpResponse("Trop de tentatives de connexion. Merci de réessayer plus tard.", status=429)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return '/gestion/'


@user_passes_test(is_chelsea, login_url='/gestion/connexion/')
def dashboard_view(request):
    today = timezone.now().date()
    
    # Rendez-vous du jour
    today_appointments = Appointment.objects.filter(
        starts_at__date=today
    ).select_related('customer', 'service').order_by('starts_at')

    # Demandes en attente de confirmation
    pending_appointments = Appointment.objects.filter(
        status='pending'
    ).select_related('customer', 'service').order_by('starts_at')

    # Prochains rendez-vous confirmés
    confirmed_appointments = Appointment.objects.filter(
        status='confirmed',
        starts_at__gte=timezone.now()
    ).select_related('customer', 'service').order_by('starts_at')[:5]

    # Annulations récentes
    recent_cancellations = Appointment.objects.filter(
        status__in=['cancelled_by_customer', 'cancelled_by_admin', 'declined']
    ).select_related('customer', 'service').order_by('-updated_at')[:5]

    # Revenus estimés ce mois-ci
    first_day_month = today.replace(day=1)
    monthly_revenue = Appointment.objects.filter(
        status__in=['confirmed', 'completed'],
        starts_at__date__gte=first_day_month
    ).aggregate(total=Sum('quoted_price'))['total'] or 0

    pending_rows = [
        appointment_row(
            a, a.customer.full_name,
            f"{a.service.name} · {timezone.localtime(a.starts_at):%d/%m %H:%M}",
        ) for a in pending_appointments
    ]
    today_rows = [
        appointment_row(
            a, f"{timezone.localtime(a.starts_at):%H:%M} · {a.customer.full_name}",
            f"{a.service.name} · {a.quoted_price} €",
        ) for a in today_appointments
    ]
    confirmed_rows = [
        appointment_row(
            a, a.customer.full_name,
            f"{timezone.localtime(a.starts_at):%d/%m/%Y %H:%M} · {a.service.name}",
        ) for a in confirmed_appointments
    ]
    cancellation_rows = [
        appointment_row(
            a, a.customer.full_name,
            f"{a.service.name} · {timezone.localtime(a.starts_at):%d/%m/%Y %H:%M}",
        ) for a in recent_cancellations
    ]

    context = {
        'today_count': len(today_rows),
        'pending_rows': pending_rows,
        'today_rows': today_rows,
        'confirmed_rows': confirmed_rows,
        'cancellation_rows': cancellation_rows,
        'pending_count': len(pending_rows),
        'confirmed_count': len(confirmed_rows),
        'monthly_revenue_display': f"{monthly_revenue} €",
        'meta_title': "Tableau de bord - Gestion Chelsea",
    }
    return render(request, 'gestion/dashboard.html', context)


@user_passes_test(is_chelsea, login_url='/gestion/connexion/')
def appointment_list_view(request):
    status_filter = request.GET.get('status')
    appointments_qs = Appointment.objects.select_related('customer', 'service').order_by('-starts_at')

    if status_filter:
        appointments_qs = appointments_qs.filter(status=status_filter)

    appointment_rows = [
        appointment_row(
            a, f"{timezone.localtime(a.starts_at):%d/%m/%Y %H:%M} · {a.customer.full_name}",
            f"{a.service.name} · {a.customer.phone} · {a.quoted_price} €",
        ) for a in appointments_qs
    ]

    context = {
        'appointment_rows': appointment_rows,
        'current_status': status_filter or 'all',
        'meta_title': "Gestion des Rendez-vous - Chelsea",
    }
    return render(request, 'gestion/appointment_list.html', context)


@user_passes_test(is_chelsea, login_url='/gestion/connexion/')
def appointment_detail_view(request, public_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related('customer', 'service'),
        public_id=public_id
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        admin_note = request.POST.get('admin_note', '')
        
        if admin_note:
            appointment.admin_note = admin_note

        if action == 'confirm':
            appointment.status = 'confirmed'
            appointment.save()
            EmailService.send_notification(appointment, 'confirmed')
            messages.success(request, "Rendez-vous confirmé ! Un courriel a été envoyé au client.")
        elif action == 'decline':
            appointment.status = 'declined'
            appointment.save()
            EmailService.send_notification(appointment, 'declined')
            messages.info(request, "Rendez-vous refusé. Le client a été notifié par email.")
        elif action == 'complete':
            appointment.status = 'completed'
            appointment.save()
            messages.success(request, "Rendez-vous marqué comme terminé.")
        elif action == 'no_show':
            appointment.status = 'no_show'
            appointment.save()
            messages.warning(request, "Rendez-vous marqué comme absent / non honoré.")
        elif action == 'cancel_admin':
            appointment.status = 'cancelled_by_admin'
            appointment.save()
            EmailService.send_notification(appointment, 'cancelled')
            messages.info(request, "Rendez-vous annulé.")
        elif action == 'update_note':
            appointment.save()
            messages.success(request, "Note interne mise à jour.")

        return redirect('accounts:gestion_appointment_detail', public_id=appointment.public_id)

    context = {
        'appointment': appointment,
        'meta_title': f"RDV {appointment.customer.full_name} - Gestion Chelsea",
    }
    return render(request, 'gestion/appointment_detail.html', context)


def _business_day_status(a_date):
    """Statut visuel d'une journée pour l'agenda de gestion : vert = ouverte, rouge = fermée/bloquée toute la journée."""
    business_hour = BusinessHours.objects.filter(weekday=a_date.weekday()).first()
    if not business_hour or business_hour.is_closed:
        return 'unavailable'

    full_day_blocked = BlockedPeriod.objects.filter(
        all_day=True,
        starts_at__date__lte=a_date,
        ends_at__date__gte=a_date,
    ).exists()
    if full_day_blocked:
        return 'unavailable'

    return 'available'


def _build_gestion_calendar_context(request):
    today = timezone.now().date()
    try:
        year = int(request.GET.get('year') or today.year)
        month = int(request.GET.get('month') or today.month)
    except (TypeError, ValueError):
        year, month = today.year, today.month

    selected_date_str = request.GET.get('date')
    selected_date = None
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = None
    elif not request.GET.get('year') and not request.GET.get('month'):
        # Chargement initial de la page : on affiche la journée du jour par défaut.
        selected_date = today

    weeks = build_month_grid(year, month, _business_day_status, today=today)
    (prev_year, prev_month), (next_year, next_month) = adjacent_months(year, month)

    day_rows = None
    if selected_date:
        day_appointments = Appointment.objects.filter(
            starts_at__date=selected_date
        ).select_related('customer', 'service').order_by('starts_at')
        day_rows = [
            appointment_row(
                a, f"{timezone.localtime(a.starts_at):%H:%M} · {a.customer.full_name}",
                f"{a.service.name} · fin {timezone.localtime(a.ends_at):%H:%M}",
            ) for a in day_appointments
        ]

    return {
        'calendar_weeks': weeks,
        'calendar_month_label': month_label(year, month),
        'calendar_year': year,
        'calendar_month': month,
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'selected_date': selected_date,
        'day_rows': day_rows,
    }


@user_passes_test(is_chelsea, login_url='/gestion/connexion/')
def calendar_view(request):
    context = {
        'meta_title': "Agenda & Planning - Gestion Chelsea",
        **_build_gestion_calendar_context(request),
    }
    return render(request, 'gestion/calendar.html', context)


@user_passes_test(is_chelsea, login_url='/gestion/connexion/')
def calendar_partial_view(request):
    """Endpoint HTMX : régénère le calendrier + le détail du jour sélectionné sans recharger la page."""
    return render(request, 'gestion/partials/calendar.html', _build_gestion_calendar_context(request))


@user_passes_test(is_chelsea, login_url='/gestion/connexion/')
def services_gestion_view(request):
    services = Service.objects.all().select_related('category')
    context = {
        'services': services,
        'meta_title': "Gestion des Services - Chelsea",
    }
    return render(request, 'gestion/services_list.html', context)


@user_passes_test(is_chelsea, login_url='/gestion/connexion/')
def gallery_gestion_view(request):
    gallery_items = GalleryItem.objects.all().select_related('related_service')
    context = {
        'gallery_items': gallery_items,
        'meta_title': "Gestion de la Galerie - Chelsea",
    }
    return render(request, 'gestion/gallery_list.html', context)


@user_passes_test(is_chelsea, login_url='/gestion/connexion/')
def hours_gestion_view(request):
    hours = BusinessHours.objects.all().order_by('weekday')

    if request.method == 'POST':
        for bh in hours:
            is_closed = request.POST.get(f'closed_{bh.id}') == 'on'
            opening = request.POST.get(f'opening_{bh.id}', '09:00')
            closing = request.POST.get(f'closing_{bh.id}', '19:00')
            bh.is_closed = is_closed
            if not is_closed:
                bh.opening_time = opening
                bh.closing_time = closing
            bh.save()
        messages.success(request, "Horaires d'ouverture mis à jour avec succès.")
        return redirect('accounts:gestion_hours')

    context = {
        'hours': hours,
        'meta_title': "Gestion des Horaires - Chelsea",
    }
    return render(request, 'gestion/hours.html', context)


@user_passes_test(is_chelsea, login_url='/gestion/connexion/')
def blocks_gestion_view(request):
    blocks = BlockedPeriod.objects.all().order_by('-starts_at')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            starts_at = request.POST.get('starts_at')
            ends_at = request.POST.get('ends_at')
            reason = request.POST.get('reason', '')
            if starts_at and ends_at:
                BlockedPeriod.objects.create(
                    starts_at=starts_at,
                    ends_at=ends_at,
                    reason=reason
                )
                messages.success(request, "Période bloquée ajoutée.")
        elif action == 'delete':
            block_id = request.POST.get('block_id')
            BlockedPeriod.objects.filter(pk=block_id).delete()
            messages.info(request, "Période bloquée supprimée.")
        return redirect('accounts:gestion_blocks')

    context = {
        'blocks': blocks,
        'meta_title': "Gestion des Blocages - Chelsea",
    }
    return render(request, 'gestion/blocks.html', context)


@user_passes_test(is_chelsea, login_url='/gestion/connexion/')
def settings_gestion_view(request):
    site_settings = SiteSettings.get_solo()

    if request.method == 'POST':
        site_settings.owner_name = request.POST.get('owner_name', site_settings.owner_name)
        site_settings.business_name = request.POST.get('business_name', site_settings.business_name)
        site_settings.phone = request.POST.get('phone', site_settings.phone)
        site_settings.email = request.POST.get('email', site_settings.email)
        site_settings.short_bio = request.POST.get('short_bio', site_settings.short_bio)
        site_settings.address = request.POST.get('address', site_settings.address)
        site_settings.booking_notice = request.POST.get('booking_notice', site_settings.booking_notice)
        site_settings.cancellation_policy = request.POST.get('cancellation_policy', site_settings.cancellation_policy)
        site_settings.instagram_url = request.POST.get('instagram_url', site_settings.instagram_url)
        site_settings.tiktok_url = request.POST.get('tiktok_url', site_settings.tiktok_url)
        site_settings.whatsapp_url = request.POST.get('whatsapp_url', site_settings.whatsapp_url)
        site_settings.save()
        messages.success(request, "Paramètres du profil mis à jour.")
        return redirect('accounts:gestion_settings')

    context = {
        'site_settings': site_settings,
        'meta_title': "Paramètres du Profil - Chelsea",
    }
    return render(request, 'gestion/settings.html', context)
