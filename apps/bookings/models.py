import uuid
import re
from django.db import models
from django.db.models import F, Q
from django.core.exceptions import ValidationError
from apps.services.models import Service

class Customer(models.Model):
    first_name = models.CharField(max_length=80, verbose_name="Prénom")
    last_name = models.CharField(max_length=80, verbose_name="Nom")
    email = models.EmailField(db_index=True, verbose_name="Adresse courriel")
    phone = models.CharField(max_length=30, db_index=True, verbose_name="Numéro de téléphone")
    notes = models.TextField(blank=True, verbose_name="Notes internes sur le client")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"
        ordering = ['last_name', 'first_name']

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.email.strip().lower()
        if self.phone:
            # Normalisation basique du téléphone (retrait des espaces superflus)
            self.phone = re.sub(r'\s+', ' ', self.phone.strip())

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return f"{self.full_name} ({self.email})"


class BusinessHours(models.Model):
    WEEKDAY_CHOICES = (
        (0, 'Lundi'),
        (1, 'Mardi'),
        (2, 'Mercredi'),
        (3, 'Jeudi'),
        (4, 'Vendredi'),
        (5, 'Samedi'),
        (6, 'Dimanche'),
    )

    weekday = models.IntegerField(choices=WEEKDAY_CHOICES, unique=True, verbose_name="Jour de la semaine")
    opening_time = models.TimeField(default="09:00", verbose_name="Heure d'ouverture")
    closing_time = models.TimeField(default="19:00", verbose_name="Heure de fermeture")
    is_closed = models.BooleanField(default=False, verbose_name="Fermé toute la journée")

    class Meta:
        verbose_name = "Horaire d'ouverture"
        verbose_name_plural = "Horaires d'ouverture"
        ordering = ['weekday']
        constraints = [
            models.CheckConstraint(
                condition=Q(is_closed=True) | Q(closing_time__gt=F('opening_time')),
                name='business_hours_valid_time_range',
            ),
        ]

    def clean(self):
        super().clean()
        if not self.is_closed:
            if self.opening_time and self.closing_time and self.closing_time <= self.opening_time:
                raise ValidationError({
                    'closing_time': "L'heure de fermeture doit être strictement supérieure à l'heure d'ouverture."
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        day_str = dict(self.WEEKDAY_CHOICES).get(self.weekday, str(self.weekday))
        if self.is_closed:
            return f"{day_str} : Fermé"
        return f"{day_str} : {self.opening_time.strftime('%H:%M')} - {self.closing_time.strftime('%H:%M')}"


class BlockedPeriod(models.Model):
    starts_at = models.DateTimeField(verbose_name="Début de la période bloquée")
    ends_at = models.DateTimeField(verbose_name="Fin de la période bloquée")
    reason = models.CharField(max_length=255, blank=True, verbose_name="Motif / Raison")
    all_day = models.BooleanField(default=False, verbose_name="Toute la journée")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    class Meta:
        verbose_name = "Période bloquée"
        verbose_name_plural = "Périodes bloquées"
        ordering = ['starts_at']
        indexes = [
            models.Index(fields=['starts_at', 'ends_at']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=F('starts_at')),
                name='blocked_period_ends_after_starts',
            ),
        ]

    def clean(self):
        super().clean()
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({
                'ends_at': "La date/heure de fin doit être strictement postérieure à la date/heure de début."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Blocage : {self.starts_at.strftime('%d/%m/%Y %H:%M')} au {self.ends_at.strftime('%d/%m/%Y %H:%M')} ({self.reason or 'Sans motif'})"


class Appointment(models.Model):
    configuration = models.JSONField(default=dict, blank=True)

    STATUS_CHOICES = (
        ('pending', 'En attente de confirmation'),
        ('confirmed', 'Confirmé'),
        ('declined', 'Refusé par Chelsea'),
        ('cancelled_by_customer', 'Annulé par le client'),
        ('cancelled_by_admin', 'Annulé par Chelsea'),
        ('completed', 'Terminé'),
        ('no_show', 'Absent / Non honoré'),
    )

    public_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        verbose_name="Identifiant public UUID"
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='appointments',
        verbose_name="Client"
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name='appointments',
        verbose_name="Service réservé"
    )
    starts_at = models.DateTimeField(verbose_name="Heure de début")
    ends_at = models.DateTimeField(verbose_name="Heure de fin")
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    quoted_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="Prix estimé (€)"
    )
    client_note = models.TextField(blank=True, verbose_name="Note / Demande particulière du client")
    admin_note = models.TextField(blank=True, verbose_name="Note interne (Chelsea)")
    confirmation_token = models.CharField(
        max_length=64,
        default=uuid.uuid4,
        editable=False,
        verbose_name="Token de confirmation / annulation"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de demande")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")

    class Meta:
        verbose_name = "Rendez-vous"
        verbose_name_plural = "Rendez-vous"
        ordering = ['-starts_at']
        indexes = [
            models.Index(fields=['status', 'starts_at']),
            models.Index(fields=['starts_at', 'ends_at']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=F('starts_at')),
                name='appointment_ends_after_starts',
            ),
        ]

    def clean(self):
        super().clean()
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({
                'ends_at': "L'heure de fin du rendez-vous doit être supérieure à l'heure de début."
            })

    def save(self, *args, **kwargs):
        if self.quoted_price is None and self.service:
            self.quoted_price = self.service.price
        super().save(*args, **kwargs)

    @property
    def configured_duration_minutes(self):
        return int((self.ends_at - self.starts_at).total_seconds() // 60)

    @property
    def is_active_booking(self):
        """Détermine si le rendez-vous bloque activement le créneau sur l'agenda"""
        return self.status in ('pending', 'confirmed')

    def __str__(self):
        return f"RDV {self.service.name} - {self.customer.full_name} le {self.starts_at.strftime('%d/%m/%Y à %H:%M')} [{self.get_status_display()}]"


class AppointmentAttachment(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='attachments')
    option_group_id_snapshot = models.PositiveIntegerField()
    name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    content = models.BinaryField()
