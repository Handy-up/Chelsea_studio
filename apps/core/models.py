from django.db import models

class SiteSettings(models.Model):
    """
    Modèle singleton représentant les paramètres globaux du salon Chelsea Coiffure.
    """
    business_name = models.CharField(
        max_length=150,
        default="Chelsea Coiffure",
        verbose_name="Nom de l'entreprise"
    )
    owner_name = models.CharField(
        max_length=100,
        default="Chelsea",
        verbose_name="Nom de la propriétaire"
    )
    profile_photo = models.ImageField(
        upload_to='profile/',
        blank=True,
        null=True,
        verbose_name="Photo de profil"
    )
    short_bio = models.TextField(
        default="Coiffeuse passionnée et experte en coupes & soins sur mesure pour hommes et femmes.",
        verbose_name="Bio courte"
    )
    email = models.EmailField(
        default="chelsea@shelsea-coiffure.fr",
        verbose_name="Adresse courriel"
    )
    phone = models.CharField(
        max_length=30,
        default="+33 6 12 34 56 78",
        verbose_name="Téléphone"
    )
    city = models.CharField(
        max_length=100,
        default="Paris",
        verbose_name="Ville"
    )
    address = models.TextField(
        default="12 Rue de la Coiffure, 75011 Paris",
        verbose_name="Adresse complète"
    )
    timezone = models.CharField(
        max_length=50,
        default="Europe/Paris",
        verbose_name="Fuseau horaire"
    )
    booking_notice = models.TextField(
        default="Réservation minimale 24h à l'avance. Merci de venir avec vos cheveux propres.",
        verbose_name="Instructions de réservation"
    )
    cancellation_policy = models.TextField(
        default="Annulation sans frais jusqu'à 24h avant le rendez-vous. En deçà, merci de contacter Chelsea directement.",
        verbose_name="Politique d'annulation"
    )
    
    # Liens réseaux sociaux
    instagram_url = models.URLField(blank=True, default="https://instagram.com", verbose_name="URL Instagram")
    tiktok_url = models.URLField(blank=True, default="https://tiktok.com", verbose_name="URL TikTok")
    facebook_url = models.URLField(blank=True, default="https://facebook.com", verbose_name="URL Facebook")
    whatsapp_url = models.URLField(blank=True, default="https://wa.me/33612345678", verbose_name="URL WhatsApp")

    class Meta:
        verbose_name = "Paramètres du site"
        verbose_name_plural = "Paramètres du site"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"Paramètres de {self.business_name}"
