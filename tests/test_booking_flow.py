import re
import json
from apps.services.models import ClientType

import pytest

from apps.bookings.forms import BookingCustomerForm
from apps.bookings.models import Appointment
from apps.notifications.models import EmailLog
from tests.conftest import aware_at


pytestmark = pytest.mark.django_db


def _booking_nonce(response, client, service):
    match = re.search(r'name="booking_nonce" value="([^"]+)"', response.content.decode())
    assert match
    kind = ClientType.objects.create(name='Client', slug='booking-client')
    configured = client.post('/reservation/configurer/', {'selection': json.dumps({
        'clientTypeId': str(kind.pk), 'categoryId': str(service.pk), 'selectedOptions': {},
    })})
    assert configured.status_code == 200
    return match.group(1), configured.json()['token']


def test_booking_view_creates_pending_appointment_and_email_logs(client, open_day, service, settings):
    settings.BOOKING_MIN_NOTICE_HOURS = 0
    response = client.get(f'/reservation/?service={service.id}')
    nonce, token = _booking_nonce(response, client, service)
    starts_at = aware_at(open_day, 10)

    response = client.post('/reservation/', {
        'action': 'submit_booking',
        'service_id': service.id,
        'date': open_day.isoformat(),
        'slot': starts_at.isoformat(),
        'booking_nonce': nonce,
        'configuration_token': token,
        'first_name': 'Maya',
        'last_name': 'Dubois',
        'email': 'maya@example.com',
        'phone': '5145550101',
        'client_note': 'Merci',
        'accept_policy': 'on',
    })

    assert response.status_code == 302
    appointment = Appointment.objects.get()
    assert appointment.status == 'pending'
    assert appointment.public_id.hex in response['Location'].replace('-', '')
    assert EmailLog.objects.count() == 2


def test_booking_nonce_prevents_identical_double_submit(client, open_day, service, settings):
    settings.BOOKING_MIN_NOTICE_HOURS = 0
    nonce, token = _booking_nonce(client.get(f'/reservation/?service={service.id}'), client, service)
    starts_at = aware_at(open_day, 14)
    payload = {
        'action': 'submit_booking',
        'service_id': service.id,
        'date': open_day.isoformat(),
        'slot': starts_at.isoformat(),
        'booking_nonce': nonce,
        'configuration_token': token,
        'first_name': 'Maya',
        'last_name': 'Dubois',
        'email': 'maya@example.com',
        'phone': '5145550101',
        'accept_policy': 'on',
    }

    assert client.post('/reservation/', payload).status_code == 302
    second_response = client.post('/reservation/', payload)

    assert second_response.status_code == 200
    assert Appointment.objects.count() == 1


def test_booking_form_honeypot_rejects_spam():
    form = BookingCustomerForm(data={
        'first_name': 'Maya',
        'last_name': 'Dubois',
        'email': 'maya@example.com',
        'phone': '5145550101',
        'accept_policy': 'on',
        'website_hp': 'bot',
    })

    assert not form.is_valid()
    assert 'website_hp' in form.errors


def test_customer_can_cancel_with_public_uuid_and_token(client, open_day, service, settings):
    settings.BOOKING_MIN_NOTICE_HOURS = 0
    nonce, token = _booking_nonce(client.get(f'/reservation/?service={service.id}'), client, service)
    starts_at = aware_at(open_day, 15)
    client.post('/reservation/', {
        'action': 'submit_booking',
        'service_id': service.id,
        'date': open_day.isoformat(),
        'slot': starts_at.isoformat(),
        'booking_nonce': nonce,
        'configuration_token': token,
        'first_name': 'Maya',
        'last_name': 'Dubois',
        'email': 'maya@example.com',
        'phone': '5145550101',
        'accept_policy': 'on',
    })
    appointment = Appointment.objects.get()

    response = client.post(f'/reservation/annuler/{appointment.public_id}/{appointment.confirmation_token}/')

    assert response.status_code == 302
    appointment.refresh_from_db()
    assert appointment.status == 'cancelled_by_customer'
