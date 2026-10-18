from django.contrib import admin
from .models import EmailLog


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('sent_at', 'email_type', 'recipient', 'status', 'appointment', 'provider_message_id')
    list_filter = ('status', 'email_type', 'sent_at')
    search_fields = ('recipient', 'provider_message_id', 'error_message', 'appointment__public_id')
    readonly_fields = ('appointment', 'email_type', 'recipient', 'provider_message_id', 'status', 'sent_at', 'error_message')
    ordering = ('-sent_at',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
