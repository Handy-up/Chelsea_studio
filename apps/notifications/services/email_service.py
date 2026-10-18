import logging
import requests
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from apps.notifications.models import EmailLog

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def send_notification(appointment, email_type, recipient=None, extra_context=None):
        """
        Envoie un courriel transactionnel et enregistre la tentative dans EmailLog.
        Ne lève jamais d'exception pour ne pas annuler la transaction de réservation.
        """
        context = {
            'appointment': appointment,
            'customer': appointment.customer if appointment else None,
            'service': appointment.service if appointment else None,
            'site_name': "Chelsea Coiffure",
        }
        if extra_context:
            context.update(extra_context)

        subject_map = {
            'confirmation_request': "Demande de rendez-vous reçue - Chelsea Coiffure",
            'new_appointment_admin': "Nouveau rendez-vous en attente de confirmation !",
            'confirmed': "Votre rendez-vous est confirmé avec Chelsea !",
            'declined': "Mise à jour concernant votre demande de rendez-vous",
            'rescheduled': "Votre rendez-vous a été déplacé - Chelsea Coiffure",
            'cancelled': "Confirmation d'annulation de rendez-vous",
            'reminder': "Rappel : Votre rendez-vous approche avec Chelsea",
        }

        subject = subject_map.get(email_type, "Information concernant votre rendez-vous")

        if not recipient:
            if email_type == 'new_appointment_admin':
                recipient = settings.ADMIN_EMAIL
            elif appointment and appointment.customer:
                recipient = appointment.customer.email
            else:
                logger.error("Aucun destinataire fourni pour l'envoi de l'email.")
                return False

        template_prefix = f"emails/{email_type}"
        
        try:
            html_content = render_to_string(f"{template_prefix}.html", context)
        except Exception:
            html_content = f"<p>{subject}</p><p>Rendez-vous : {appointment}</p>"

        try:
            text_content = render_to_string(f"{template_prefix}.txt", context)
        except Exception:
            text_content = strip_tags(html_content)

        resend_api_key = getattr(settings, 'RESEND_API_KEY', '')
        provider_message_id = ""
        status = 'sent'
        error_msg = ""

        try:
            if resend_api_key:
                # Utiliser l'API Resend HTTP
                url = "https://api.resend.com/emails"
                headers = {
                    "Authorization": f"Bearer {resend_api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "from": getattr(settings, 'DEFAULT_FROM_EMAIL', 'contact@shelsea-coiffure.fr'),
                    "to": [recipient],
                    "subject": subject,
                    "html": html_content,
                    "text": text_content,
                }
                response = requests.post(url, json=payload, headers=headers, timeout=5)
                if response.status_code in (200, 201):
                    data = response.json()
                    provider_message_id = data.get('id', '')
                else:
                    # En cas d'erreur Resend, basculer sur le backend standard Django
                    logger.warning(f"Erreur API Resend ({response.status_code}): {response.text}. Repli sur send_mail standard.")
                    send_mail(
                        subject,
                        text_content,
                        settings.DEFAULT_FROM_EMAIL,
                        [recipient],
                        html_message=html_content,
                        fail_silently=False
                    )
            else:
                # Utiliser le backend Django configuré (Console en dev / SMTP)
                send_mail(
                    subject,
                    text_content,
                    settings.DEFAULT_FROM_EMAIL,
                    [recipient],
                    html_message=html_content,
                    fail_silently=False
                )
        except Exception as e:
            logger.error(f"Échec de l'envoi de l'email {email_type} à {recipient}: {e}")
            status = 'failed'
            error_msg = str(e)

        # Journalisation dans EmailLog
        try:
            EmailLog.objects.create(
                appointment=appointment,
                email_type=email_type,
                recipient=recipient,
                provider_message_id=provider_message_id,
                status=status,
                error_message=error_msg
            )
        except Exception as log_err:
            logger.error(f"Impossible de créer EmailLog: {log_err}")

        return status == 'sent'
