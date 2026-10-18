from django.db import models
from django.utils.text import slugify

class ServiceCategory(models.Model):
    AUDIENCE_CHOICES = (
        ('men', 'Hommes'),
        ('women', 'Femmes'),
        ('unisex', 'Unisex'),
    )

    name = models.CharField(max_length=100, verbose_name="Nom de la catégorie")
    slug = models.SlugField(max_length=120, unique=True, verbose_name="Slug URL")
    audience = models.CharField(max_length=10, choices=AUDIENCE_CHOICES, default='unisex', verbose_name="Public cible")
    description = models.TextField(blank=True, verbose_name="Description")
    image = models.ImageField(upload_to='categories/', blank=True, null=True, verbose_name="Image d'illustration")
    display_order = models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage")
    is_active = models.BooleanField(default=True, verbose_name="Actif")

    class Meta:
        verbose_name = "Catégorie de service"
        verbose_name_plural = "Catégories de services"
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['audience', 'is_active', 'display_order']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.get_audience_display()})"


class Service(models.Model):
    client_types = models.ManyToManyField("ClientType", blank=True, related_name="services", help_text="Vide : disponible pour tous les types de clients actifs.")
    PRICE_TYPE_CHOICES = (
        ('fixed', 'Prix fixe'),
        ('starting_at', 'À partir de'),
        ('consultation_required', 'Sur devis / Consultation'),
    )

    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='services',
        verbose_name="Catégorie"
    )
    name = models.CharField(max_length=150, verbose_name="Nom du service")
    slug = models.SlugField(max_length=160, unique=True, verbose_name="Slug URL")
    short_description = models.CharField(max_length=255, verbose_name="Description courte")
    full_description = models.TextField(blank=True, verbose_name="Description complète")
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, verbose_name="Prix (€)")
    price_type = models.CharField(max_length=30, choices=PRICE_TYPE_CHOICES, default='fixed', verbose_name="Type de prix")
    duration_minutes = models.PositiveIntegerField(default=60, verbose_name="Durée (minutes)")
    buffer_before_minutes = models.PositiveIntegerField(default=0, verbose_name="Buffer avant (minutes)")
    buffer_after_minutes = models.PositiveIntegerField(default=0, verbose_name="Buffer après (minutes)")
    
    client_must_bring = models.TextField(blank=True, verbose_name="Ce que le client doit apporter")
    preparation_instructions = models.TextField(blank=True, verbose_name="Instructions de préparation")
    included_materials = models.TextField(blank=True, verbose_name="Matériel inclus")
    cancellation_notes = models.TextField(blank=True, verbose_name="Conditions spécifiques d'annulation")
    
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    is_featured = models.BooleanField(default=False, verbose_name="Mettre en avant sur l'accueil")
    display_order = models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")

    class Meta:
        verbose_name = "Service"
        verbose_name_plural = "Services"
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['is_active', 'is_featured', 'display_order']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def total_block_duration(self):
        """Durée totale bloquée sur l'agenda = buffer_before + duration + buffer_after"""
        return self.buffer_before_minutes + self.duration_minutes + self.buffer_after_minutes

    @property
    def formatted_price(self):
        if self.price_type == 'starting_at':
            return f"À partir de {self.price:.2f} €"
        elif self.price_type == 'consultation_required':
            return "Sur devis"
        return f"{self.price:.2f} €"

    def get_cover_image_url(self):
        cover = self.images.filter(is_cover=True).first()
        if not cover:
            cover = self.images.first()
        if cover and cover.image:
            return cover.image.url
        return "/static/images/placeholders/service_default.svg"

    def __str__(self):
        return f"{self.name} ({self.duration_minutes} min - {self.formatted_price})"


class ServiceImage(models.Model):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name="Service"
    )
    image = models.ImageField(upload_to='services/', verbose_name="Image")
    alt_text = models.CharField(max_length=255, blank=True, verbose_name="Texte alternatif (SEO)")
    display_order = models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage")
    is_cover = models.BooleanField(default=False, verbose_name="Image de couverture")

    class Meta:
        verbose_name = "Image de service"
        verbose_name_plural = "Images de service"
        ordering = ['display_order', 'id']

    def __str__(self):
        return f"Image pour {self.service.name}"


class ConfigurableEntity(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        abstract = True
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class ClientType(ConfigurableEntity):
    pass


class HairstyleSubcategory(ConfigurableEntity):
    category = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='subcategories')
    image = models.ImageField(upload_to='styles/', blank=True)
    price_adjustment = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    duration_adjustment_minutes = models.IntegerField(default=0)


class HairstyleOptionGroup(ConfigurableEntity):
    INPUT_TYPES = [(value, value) for value in (
        'single_select', 'multi_select', 'boolean', 'text', 'textarea', 'number', 'photo', 'file'
    )]
    input_type = models.CharField(max_length=20, choices=INPUT_TYPES)
    is_required = models.BooleanField(default=False)


class HairstyleOptionValue(models.Model):
    option_group = models.ForeignKey(HairstyleOptionGroup, on_delete=models.CASCADE, related_name='values')
    label = models.CharField(max_length=150)
    value = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='options/', blank=True)
    price_adjustment = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    duration_adjustment_minutes = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'pk']
        constraints = [models.UniqueConstraint(fields=['option_group', 'value'], name='unique_option_value')]

    def __str__(self):
        return self.label


class HairstyleOptionAssignment(models.Model):
    category = models.ForeignKey(Service, null=True, blank=True, on_delete=models.CASCADE, related_name='option_assignments')
    subcategory = models.ForeignKey(HairstyleSubcategory, null=True, blank=True, on_delete=models.CASCADE, related_name='option_assignments')
    option_group = models.ForeignKey(HairstyleOptionGroup, on_delete=models.CASCADE)
    is_required = models.BooleanField(null=True, blank=True, help_text='Vide : reprendre le réglage du groupe.')
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'pk']
        constraints = [
            models.CheckConstraint(condition=(models.Q(category__isnull=False, subcategory__isnull=True) | models.Q(category__isnull=True, subcategory__isnull=False)), name='option_assignment_one_target'),
            models.UniqueConstraint(fields=['category', 'option_group'], name='unique_category_group'),
            models.UniqueConstraint(fields=['subcategory', 'option_group'], name='unique_subcategory_group'),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        if bool(self.category_id) == bool(self.subcategory_id):
            raise ValidationError('Choisissez une prestation OU un style.')
