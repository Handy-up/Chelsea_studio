from django.contrib import admin
from django.utils.html import format_html
from .models import ServiceCategory, Service, ServiceImage


class ServiceImageInline(admin.TabularInline):
    model = ServiceImage
    extra = 0
    fields = ('image', 'image_preview', 'alt_text', 'display_order', 'is_cover')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:56px;border-radius:6px;" alt="">', obj.image.url)
        return ""


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'audience', 'display_order', 'is_active')
    list_filter = ('audience', 'is_active')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('display_order', 'name')
    actions = ('activate_categories', 'deactivate_categories')

    @admin.action(description="Activer les catégories sélectionnées")
    def activate_categories(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Désactiver les catégories sélectionnées")
    def deactivate_categories(self, request, queryset):
        queryset.update(is_active=False)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'price_type', 'duration_minutes', 'is_active', 'is_featured', 'display_order')
    list_filter = ('is_active', 'is_featured', 'price_type', 'category__audience')
    search_fields = ('name', 'short_description', 'full_description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    inlines = (ServiceImageInline,)
    ordering = ('display_order', 'name')
    actions = ('activate_services', 'deactivate_services', 'feature_services', 'unfeature_services')

    @admin.action(description="Activer les services sélectionnés")
    def activate_services(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Désactiver les services sélectionnés")
    def deactivate_services(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description="Mettre en avant sur l'accueil")
    def feature_services(self, request, queryset):
        queryset.update(is_featured=True)

    @admin.action(description="Retirer de l'accueil")
    def unfeature_services(self, request, queryset):
        queryset.update(is_featured=False)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ServiceImage)
class ServiceImageAdmin(admin.ModelAdmin):
    list_display = ('service', 'image_preview', 'alt_text', 'display_order', 'is_cover')
    list_filter = ('is_cover', 'service')
    search_fields = ('service__name', 'alt_text')
    readonly_fields = ('image_preview',)
    ordering = ('service', 'display_order')

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:72px;border-radius:6px;" alt="">', obj.image.url)
        return ""

    image_preview.short_description = "Aperçu"

from .models import ClientType, HairstyleSubcategory, HairstyleOptionGroup, HairstyleOptionValue, HairstyleOptionAssignment

class OptionValueInline(admin.TabularInline):
    model = HairstyleOptionValue
    extra = 0

@admin.register(HairstyleOptionGroup)
class OptionGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'input_type', 'is_required', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    inlines = (OptionValueInline,)

@admin.register(ClientType, HairstyleSubcategory)
class ConfigurationEntityAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'sort_order')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(HairstyleOptionAssignment)
class OptionAssignmentAdmin(admin.ModelAdmin):
    list_display = ('category', 'subcategory', 'option_group', 'is_required', 'sort_order')
