from django.db import models
from apps.bookings.models import Appointment

class EmailLog(models.Model):
    EMAIL_TYPE_CHOICES = (
        ('confirmation_request', 'Demande de RDV envoyée au client'),
        ('new_appointment_admin', 'Notification de nouveau RDV envoyée à Chelsea'),
        ('confirmed', 'RDV Confirmé'),
        ('declined', 'RDV Refusé'),
        ('rescheduled', 'RDV Déplacé'),
        ('cancelled', 'RDV Annulé'),
        ('reminder', 'Rappel de RDV'),
    )

    STATUS_CHOICES = (
        ('sent', 'Envoyé avec succès'),
        ('failed', 'Échec de l\'envoi'),
    )

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_logs',
        verbose_name="Rendez-vous associé"
    )
    email_type = models.CharField(
        max_length=40,
        choices=EMAIL_TYPE_CHOICES,
        verbose_name="Type d'email"
    )
    recipient = models.EmailField(verbose_name="Destinataire")
    provider_message_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Identifiant message du fournisseur (Resend ID)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='sent',
        verbose_name="Statut d'envoi"
    )
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name="Date d'envoi")
    error_message = models.TextField(blank=True, verbose_name="Détails de l'erreur le cas échéant")

    class Meta:
        verbose_name = "Journal d'email (EmailLog)"
        verbose_name_plural = "Journaux d'emails (EmailLog)"
        ordering = ['-sent_at']

    def __str__(self):
        return f"Email {self.get_email_type_display()} -> {self.recipient} [{self.get_status_display()}]"
