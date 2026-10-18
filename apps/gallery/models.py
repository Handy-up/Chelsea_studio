from django.db import models
from apps.services.models import Service

class GalleryItem(models.Model):
    AUDIENCE_CHOICES = (
        ('men', 'Hommes'),
        ('women', 'Femmes'),
        ('unisex', 'Unisex'),
    )

    image = models.ImageField(upload_to='gallery/', blank=True, null=True, verbose_name="Image de réalisation")
    title = models.CharField(max_length=150, verbose_name="Titre / Modèle")
    audience = models.CharField(max_length=10, choices=AUDIENCE_CHOICES, default='unisex', verbose_name="Public cible")
    related_service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gallery_items',
        verbose_name="Service associé"
    )
    alt_text = models.CharField(max_length=255, blank=True, verbose_name="Texte alternatif (SEO)")
    is_published = models.BooleanField(default=True, verbose_name="Publié")
    display_order = models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage")

    class Meta:
        verbose_name = "Réalisation (Galerie)"
        verbose_name_plural = "Réalisations (Galerie)"
        ordering = ['display_order', '-id']
        indexes = [
            models.Index(fields=['is_published', 'audience', 'display_order']),
        ]

    def get_image_url(self):
        if self.image:
            return self.image.url
        return "/static/images/placeholders/gallery_default.svg"

    def __str__(self):
        return f"{self.title} ({self.get_audience_display()})"
