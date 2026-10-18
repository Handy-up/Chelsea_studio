import pytest
from django.core.management import call_command

from apps.bookings.models import Appointment, BusinessHours, Customer
from apps.notifications.models import EmailLog
from apps.notifications.services.email_service import EmailService
from apps.services.models import Service
from tests.conftest import aware_at


pytestmark = pytest.mark.django_db


def test_email_service_logs_attempt(open_day, service):
    customer = Customer.objects.create(first_name="Maya", last_name="Dubois", email="maya@example.com", phone="5145550101")
    appointment = Appointment.objects.create(
        customer=customer,
        service=service,
        starts_at=aware_at(open_day, 10),
        ends_at=aware_at(open_day, 11),
        status='pending',
        quoted_price=service.price,
    )

    sent = EmailService.send_notification(appointment, 'confirmation_request')

    assert sent is True
    log = EmailLog.objects.get()
    assert log.email_type == 'confirmation_request'
    assert log.status == 'sent'


def test_seed_demo_command_creates_foundation_data():
    call_command('seed_demo', reset=True, verbosity=0)

    assert Service.objects.count() == 6
    assert BusinessHours.objects.count() == 7
    assert Appointment.objects.count() == 3
