from django.contrib import admin
from .models import Customer, BusinessHours, BlockedPeriod, Appointment


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'phone')
    readonly_fields = ('created_at',)
    ordering = ('last_name', 'first_name')

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BusinessHours)
class BusinessHoursAdmin(admin.ModelAdmin):
    list_display = ('weekday', 'opening_time', 'closing_time', 'is_closed')
    list_filter = ('is_closed',)
    ordering = ('weekday',)


@admin.register(BlockedPeriod)
class BlockedPeriodAdmin(admin.ModelAdmin):
    list_display = ('starts_at', 'ends_at', 'reason', 'all_day', 'created_at')
    list_filter = ('all_day', 'starts_at')
    search_fields = ('reason',)
    readonly_fields = ('created_at',)
    ordering = ('-starts_at',)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('starts_at', 'customer', 'service', 'status', 'quoted_price', 'public_id')
    list_filter = ('status', 'service', 'starts_at')
    search_fields = (
        'customer__first_name',
        'customer__last_name',
        'customer__email',
        'service__name',
        'public_id',
    )
    readonly_fields = ('public_id', 'confirmation_token', 'configuration', 'created_at', 'updated_at')
    date_hierarchy = 'starts_at'
    ordering = ('-starts_at',)
    actions = ('mark_confirmed', 'mark_cancelled_by_admin', 'mark_completed')

    @admin.action(description="Marquer comme confirmés")
    def mark_confirmed(self, request, queryset):
        queryset.filter(status='pending').update(status='confirmed')

    @admin.action(description="Annuler côté Chelsea")
    def mark_cancelled_by_admin(self, request, queryset):
        queryset.exclude(status__in=['completed', 'no_show']).update(status='cancelled_by_admin')

    @admin.action(description="Marquer comme terminés")
    def mark_completed(self, request, queryset):
        queryset.filter(status='confirmed').update(status='completed')

    def has_delete_permission(self, request, obj=None):
        return False
