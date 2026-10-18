from django.contrib import admin
from django.utils.html import format_html
from .models import GalleryItem


@admin.register(GalleryItem)
class GalleryItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'image_preview', 'audience', 'related_service', 'is_published', 'display_order')
    list_filter = ('audience', 'is_published', 'related_service')
    search_fields = ('title', 'alt_text', 'related_service__name')
    readonly_fields = ('image_preview',)
    ordering = ('display_order', '-id')
    actions = ('publish_items', 'unpublish_items')

    @admin.action(description="Publier les réalisations sélectionnées")
    def publish_items(self, request, queryset):
        queryset.update(is_published=True)

    @admin.action(description="Dépublier les réalisations sélectionnées")
    def unpublish_items(self, request, queryset):
        queryset.update(is_published=False)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:72px;border-radius:6px;" alt="">', obj.image.url)
        return ""

    image_preview.short_description = "Aperçu"
