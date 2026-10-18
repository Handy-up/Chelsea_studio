from django.contrib import admin
from django.utils.html import format_html
from .models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Identité', {
            'fields': ('business_name', 'owner_name', 'profile_photo', 'profile_preview', 'short_bio'),
        }),
        ('Contact', {
            'fields': ('email', 'phone', 'city', 'address', 'timezone'),
        }),
        ('Réservation', {
            'fields': ('booking_notice', 'cancellation_policy'),
        }),
        ('Réseaux sociaux', {
            'fields': ('instagram_url', 'tiktok_url', 'facebook_url', 'whatsapp_url'),
        }),
    )
    readonly_fields = ('profile_preview',)

    def profile_preview(self, obj):
        if obj.profile_photo:
            return format_html('<img src="{}" style="max-width:120px;border-radius:8px;" alt="">', obj.profile_photo.url)
        return "Aucune image"

    profile_preview.short_description = "Aperçu"

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
