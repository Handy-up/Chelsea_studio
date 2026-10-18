from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.bookings.models import Appointment, BlockedPeriod, BusinessHours, Customer
from apps.core.models import SiteSettings
from apps.gallery.models import GalleryItem
from apps.services.models import Service, ServiceCategory, ClientType


class Command(BaseCommand):
    help = "Génère des données de démonstration locales pour Chelsea."

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help="Supprime les données métier existantes avant de recréer la démo.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['reset']:
            Appointment.objects.all().delete()
            Customer.objects.all().delete()
            BlockedPeriod.objects.all().delete()
            GalleryItem.objects.all().delete()
            Service.objects.all().delete()
            ServiceCategory.objects.all().delete()

        settings = SiteSettings.get_solo()
        settings.business_name = "Chelsea Studio Coiffure"
        settings.owner_name = "Chelsea"
        settings.short_bio = "Coiffeuse indépendante, spécialisée dans les coupes nettes, les soins profonds et les finitions élégantes."
        settings.email = "chelsea@example.com"
        settings.phone = "+1 514 555 0142"
        settings.city = "Montréal"
        settings.address = "123 rue Exemple, Montréal"
        settings.timezone = "America/Toronto"
        settings.booking_notice = "Réservation au moins 2 heures à l'avance. Merci d'arriver avec les cheveux démêlés."
        settings.cancellation_policy = "Annulation possible jusqu'à 24 heures avant le rendez-vous."
        settings.instagram_url = "https://instagram.com/chelsea.demo"
        settings.tiktok_url = "https://tiktok.com/@chelsea.demo"
        settings.facebook_url = "https://facebook.com/chelsea.demo"
        settings.whatsapp_url = "https://wa.me/15145550142"
        settings.save()

        women_category, _ = ServiceCategory.objects.update_or_create(
            slug='femmes',
            defaults={
                'name': 'Femmes',
                'audience': 'women',
                'description': 'Coupes, soins et finitions pour femmes.',
                'display_order': 1,
                'is_active': True,
            },
        )
        men_category, _ = ServiceCategory.objects.update_or_create(
            slug='hommes',
            defaults={
                'name': 'Hommes',
                'audience': 'men',
                'description': 'Coupes, contours et entretien pour hommes.',
                'display_order': 2,
                'is_active': True,
            },
        )

        service_specs = [
            (women_category, 'Coupe femme signature', 'coupe-femme-signature', 'Coupe personnalisée avec finition.', 72, 'fixed', 75, True),
            (women_category, 'Brushing souple', 'brushing-souple', 'Mise en forme naturelle et tenue légère.', 45, 'fixed', 45, True),
            (women_category, 'Soin profond hydratant', 'soin-profond-hydratant', 'Soin nourrissant avec massage du cuir chevelu.', 58, 'starting_at', 60, False),
            (men_category, 'Coupe homme précise', 'coupe-homme-precise', 'Coupe courte ou mi-longue avec finitions.', 38, 'fixed', 40, True),
            (men_category, 'Contours et barbe', 'contours-et-barbe', 'Contours propres et entretien de barbe.', 30, 'fixed', 30, False),
            (women_category, 'Consultation couleur', 'consultation-couleur', 'Diagnostic personnalisé avant transformation.', 0, 'consultation_required', 30, False),
        ]

        services = []
        for category in (women_category, men_category):
            ClientType.objects.get_or_create(slug=category.slug, defaults={"name": category.name})

        for order, (category, name, slug, short_description, price, price_type, duration, featured) in enumerate(service_specs, start=1):
            service, _ = Service.objects.update_or_create(
                slug=slug,
                defaults={
                    'category': category,
                    'name': name,
                    'short_description': short_description,
                    'full_description': f"{short_description} Chelsea adapte la prestation à la texture, à la longueur et au résultat souhaité.",
                    'price': price,
                    'price_type': price_type,
                    'duration_minutes': duration,
                    'buffer_before_minutes': 5,
                    'buffer_after_minutes': 10,
                    'client_must_bring': "Photos d'inspiration si vous en avez.",
                    'preparation_instructions': "Arriver avec les cheveux propres et faciles à manipuler.",
                    'included_materials': "Produits professionnels, serviette et finition.",
                    'cancellation_notes': "Prévenir le plus tôt possible en cas d'empêchement.",
                    'is_active': True,
                    'is_featured': featured,
                    'display_order': order,
                },
            )
            service.client_types.add(ClientType.objects.get(slug=category.slug))
            services.append(service)

        for weekday, _label in BusinessHours.WEEKDAY_CHOICES:
            BusinessHours.objects.update_or_create(
                weekday=weekday,
                defaults={
                    'opening_time': time(9, 0),
                    'closing_time': time(18, 0) if weekday < 5 else time(15, 0),
                    'is_closed': weekday == 6,
                },
            )

        for index, service in enumerate(services, start=1):
            GalleryItem.objects.update_or_create(
                title=f"Réalisation démo {index}",
                defaults={
                    'image': '',
                    'audience': service.category.audience,
                    'related_service': service,
                    'alt_text': f"Placeholder local pour {service.name}",
                    'is_published': True,
                    'display_order': index,
                },
            )

        next_open_day = self._next_open_day()
        customers = [
            Customer.objects.update_or_create(
                email='maya@example.com',
                defaults={'first_name': 'Maya', 'last_name': 'Dubois', 'phone': '+1 514 555 0101'},
            )[0],
            Customer.objects.update_or_create(
                email='nathan@example.com',
                defaults={'first_name': 'Nathan', 'last_name': 'Roy', 'phone': '+1 514 555 0102'},
            )[0],
            Customer.objects.update_or_create(
                email='sofia@example.com',
                defaults={'first_name': 'Sofia', 'last_name': 'Martin', 'phone': '+1 514 555 0103'},
            )[0],
        ]

        demo_slots = [(9, 30, 'pending'), (11, 30, 'confirmed'), (14, 0, 'confirmed')]
        for customer, service, (hour, minute, status) in zip(customers, services, demo_slots):
            starts_at = timezone.make_aware(datetime.combine(next_open_day, time(hour, minute)))
            Appointment.objects.update_or_create(
                customer=customer,
                starts_at=starts_at,
                defaults={
                    'service': service,
                    'ends_at': starts_at + timedelta(minutes=service.duration_minutes),
                    'status': status,
                    'quoted_price': service.price,
                    'client_note': "Donnée de démonstration.",
                },
            )

        blocked_start = timezone.make_aware(datetime.combine(next_open_day + timedelta(days=1), time(13, 0)))
        BlockedPeriod.objects.update_or_create(
            starts_at=blocked_start,
            defaults={
                'ends_at': blocked_start + timedelta(hours=1),
                'reason': 'Pause personnelle démo',
                'all_day': False,
            },
        )

        self.stdout.write(self.style.SUCCESS("Données de démonstration Chelsea générées."))

    def _next_open_day(self):
        candidate = timezone.localdate() + timedelta(days=1)
        while candidate.weekday() == 6:
            candidate += timedelta(days=1)
        return candidate
