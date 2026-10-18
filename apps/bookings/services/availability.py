from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from apps.core.models import SiteSettings
from apps.bookings.models import BusinessHours, BlockedPeriod, Appointment, Customer, AppointmentAttachment


class SlotUnavailableError(Exception):
    """Exception levée lorsque le créneau sélectionné n'est plus disponible."""
    pass


class AvailabilityService:
    @staticmethod
    def get_business_timezone():
        site_settings = SiteSettings.get_solo()
        try:
            return ZoneInfo(site_settings.timezone)
        except ZoneInfoNotFoundError:
            return timezone.get_current_timezone()

    @staticmethod
    def get_booking_window(now=None):
        now = now or timezone.now()
        min_notice = timedelta(hours=getattr(settings, 'BOOKING_MIN_NOTICE_HOURS', 2))
        max_days = getattr(settings, 'BOOKING_MAX_DAYS_AHEAD', 60)
        return now + min_notice, now + timedelta(days=max_days)

    @staticmethod
    def get_available_slots(service, target_date, step_minutes=30, limit=None):
        """
        Calcule la liste des créneaux horaires disponibles pour un service donné à une date donnée.
        Rends une liste de dictionnaires [{'time': '09:00', 'datetime': dt_obj, 'formatted': '09h00'}]

        `limit` permet de s'arrêter dès que N créneaux ont été trouvés (utile pour ne
        vérifier que la simple disponibilité d'une journée, par ex. pour un calendrier mensuel).
        """
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()

        business_tz = AvailabilityService.get_business_timezone()
        now = timezone.localtime(timezone.now(), business_tz)
        min_notice_dt, max_booking_dt = AvailabilityService.get_booking_window(now)
        
        if target_date < now.date() or target_date > max_booking_dt.date():
            return []

        # 2. Vérifier les horaires d'ouverture pour ce jour
        weekday = target_date.weekday() # 0 = Lundi, 6 = Dimanche
        business_hour = BusinessHours.objects.filter(weekday=weekday).first()
        if not business_hour or business_hour.is_closed:
            return []

        # Combiner date et heure pour créer les datetimes de début et fin de journée d'ouverture
        day_open_dt = timezone.make_aware(datetime.combine(target_date, business_hour.opening_time), business_tz)
        day_close_dt = timezone.make_aware(datetime.combine(target_date, business_hour.closing_time), business_tz)

        # 3. Récupérer les rendez-vous existants actifs et les périodes bloquées pour la journée
        # On élargit légèrement la fenêtre pour intercepter les chevauchements avec buffers
        window_start = day_open_dt - timedelta(hours=3)
        window_end = day_close_dt + timedelta(hours=3)

        existing_appointments = Appointment.objects.filter(
            status__in=['pending', 'confirmed'],
            starts_at__lt=window_end,
            ends_at__gt=window_start
        ).select_related('service')

        blocked_periods = BlockedPeriod.objects.filter(
            starts_at__lt=window_end,
            ends_at__gt=window_start
        )

        # Durée totale bloquée sur le planning par ce soin = buffer_before + duration + buffer_after
        total_block_minutes = service.buffer_before_minutes + service.duration_minutes + service.buffer_after_minutes
        service_duration_td = timedelta(minutes=total_block_minutes)

        slots = []
        current_time_dt = day_open_dt
        while current_time_dt + service_duration_td <= day_close_dt:
            # L'intervalle complet occupé par la prestation (y compris tampons avant/après)
            slot_block_start = current_time_dt
            slot_block_end = current_time_dt + service_duration_td

            # Heure exacte où la cliente est sur la chaise (après le buffer avant)
            appointment_start = slot_block_start + timedelta(minutes=service.buffer_before_minutes)
            appointment_end = appointment_start + timedelta(minutes=service.duration_minutes)

            # Ne pas proposer de créneau dans le passé ou trop proche
            if appointment_start < min_notice_dt:
                current_time_dt += timedelta(minutes=step_minutes)
                continue

            # Vérification des chevauchements avec les rendez-vous existants
            overlap = False
            for appt in existing_appointments:
                # Intervalle total occupé par l'existant (avec ses propres buffers)
                appt_total_start = appt.starts_at - timedelta(minutes=appt.service.buffer_before_minutes)
                appt_total_end = appt.ends_at + timedelta(minutes=appt.service.buffer_after_minutes)

                if max(slot_block_start, appt_total_start) < min(slot_block_end, appt_total_end):
                    overlap = True
                    break

            if not overlap:
                # Vérification des périodes bloquées
                for block in blocked_periods:
                    if max(slot_block_start, block.starts_at) < min(slot_block_end, block.ends_at):
                        overlap = True
                        break

            if not overlap:
                slots.append({
                    'time_str': appointment_start.strftime('%H:%M'),
                    'formatted': appointment_start.strftime('%Hh%M'),
                    'starts_at_iso': appointment_start.isoformat(),
                    'ends_at_iso': appointment_end.isoformat(),
                    'block_start_iso': slot_block_start.isoformat(),
                    'block_end_iso': slot_block_end.isoformat(),
                })
                if limit is not None and len(slots) >= limit:
                    break

            current_time_dt += timedelta(minutes=step_minutes)

        return slots

    @staticmethod
    def has_availability(service, target_date):
        """Retourne True dès qu'au moins un créneau est disponible ce jour-là (calcul allégé pour un calendrier)."""
        return len(AvailabilityService.get_available_slots(service, target_date, limit=1)) > 0

    @staticmethod
    @transaction.atomic
    def book_appointment(customer_data, service, starts_at_dt, client_note="", configuration=None, files=None):
        """
        Crée un rendez-vous de manière transactionnelle avec verrouillage et re-validation stricte.
        """
        quote = None
        if configuration is not None:
            from apps.services.services.configuration import resolve_configuration
            from django.core.exceptions import ValidationError
            quote = resolve_configuration(configuration, files, require_uploads=True)
            if quote.snapshot != configuration:
                raise ValidationError('Le soin a changé. Vérifiez à nouveau votre sélection.')
            service = quote
        if isinstance(starts_at_dt, str):
            starts_at_dt = datetime.fromisoformat(starts_at_dt)

        business_tz = AvailabilityService.get_business_timezone()
        if timezone.is_naive(starts_at_dt):
            starts_at_dt = timezone.make_aware(starts_at_dt, business_tz)
        else:
            starts_at_dt = timezone.localtime(starts_at_dt, business_tz)

        if not service.is_active:
            raise SlotUnavailableError("Ce service n'est plus disponible à la réservation.")

        ends_at_dt = starts_at_dt + timedelta(minutes=service.duration_minutes)
        block_start = starts_at_dt - timedelta(minutes=service.buffer_before_minutes)
        block_end = ends_at_dt + timedelta(minutes=service.buffer_after_minutes)

        # 1. Vérification dans la fenêtre sous verrouillage d'ouverture
        target_date = starts_at_dt.date()
        weekday = target_date.weekday()
        business_hour = BusinessHours.objects.select_for_update().filter(weekday=weekday).first()
        
        if not business_hour or business_hour.is_closed:
            raise SlotUnavailableError("Le salon est fermé à cette date.")

        day_open_dt = timezone.make_aware(datetime.combine(target_date, business_hour.opening_time), business_tz)
        day_close_dt = timezone.make_aware(datetime.combine(target_date, business_hour.closing_time), business_tz)

        if block_start < day_open_dt or block_end > day_close_dt:
            raise SlotUnavailableError("Le créneau dépasse les heures d'ouverture du salon.")

        min_notice_dt, max_booking_dt = AvailabilityService.get_booking_window(timezone.localtime(timezone.now(), business_tz))
        if starts_at_dt < min_notice_dt:
            raise SlotUnavailableError("Ce créneau est trop proche. Merci de choisir une heure plus tardive.")
        if starts_at_dt > max_booking_dt:
            raise SlotUnavailableError("Ce créneau est trop éloigné dans le calendrier.")

        # 2. Verrouillage FOR UPDATE sur les rendez-vous existants chevauchant la période
        existing_conflicts = Appointment.objects.select_for_update().select_related('service').filter(
            status__in=['pending', 'confirmed'],
            starts_at__lt=block_end + timedelta(hours=2),
            ends_at__gt=block_start - timedelta(hours=2)
        )

        for appt in existing_conflicts:
            appt_total_start = appt.starts_at - timedelta(minutes=appt.service.buffer_before_minutes)
            appt_total_end = appt.ends_at + timedelta(minutes=appt.service.buffer_after_minutes)
            if max(block_start, appt_total_start) < min(block_end, appt_total_end):
                raise SlotUnavailableError("Ce créneau vient tout juste d'être réservé par un autre client.")

        # 3. Vérifier les blocages de la période
        blocked = BlockedPeriod.objects.select_for_update().filter(
            starts_at__lt=block_end,
            ends_at__gt=block_start
        ).exists()
        
        if blocked:
            raise SlotUnavailableError("Cette période est bloquée par le salon.")

        # 4. Obtenir ou créer le profil Customer, AppointmentAttachment
        customer, _ = Customer.objects.get_or_create(
            email=customer_data['email'].strip().lower(),
            defaults={
                'first_name': customer_data['first_name'].strip(),
                'last_name': customer_data['last_name'].strip(),
                'phone': customer_data['phone'].strip(),
            }
        )
        # Mettre à jour les infos si modifiées
        customer.first_name = customer_data['first_name'].strip()
        customer.last_name = customer_data['last_name'].strip()
        customer.phone = customer_data['phone'].strip()
        customer.save()

        # 5. Enregistrer le rendez-vous
        appointment = Appointment.objects.create(
            customer=customer,
            service=quote.service if quote else service,
            starts_at=starts_at_dt,
            ends_at=ends_at_dt,
            status='pending',
            quoted_price=service.price,
            client_note=client_note,
            configuration=quote.snapshot if quote else {},
        )

        if quote:
            for group_id, upload, mime in quote.uploads:
                AppointmentAttachment.objects.create(appointment=appointment, option_group_id_snapshot=group_id,
                    name=upload.name[:255], content_type=mime, content=upload.read())
        return appointment
