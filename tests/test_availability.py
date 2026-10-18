from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError

from apps.bookings.models import Appointment, BlockedPeriod, BusinessHours, Customer
from apps.bookings.services.availability import AvailabilityService, SlotUnavailableError
from tests.conftest import aware_at


pytestmark = pytest.mark.django_db


def test_available_slots_respect_open_hours(open_day, service):
    slots = AvailabilityService.get_available_slots(service, open_day)

    assert slots
    assert slots[0]['time_str'] == '09:00'
    assert slots[-1]['time_str'] == '16:00'


def test_closed_day_returns_no_slots(open_day, service):
    BusinessHours.objects.filter(weekday=open_day.weekday()).update(is_closed=True)

    assert AvailabilityService.get_available_slots(service, open_day) == []


def test_blocked_period_removes_overlapping_slots(open_day, service):
    BlockedPeriod.objects.create(
        starts_at=aware_at(open_day, 10),
        ends_at=aware_at(open_day, 11),
        reason="Pause",
    )

    slots = AvailabilityService.get_available_slots(service, open_day)

    assert '10:00' not in {slot['time_str'] for slot in slots}


def test_existing_appointment_buffer_blocks_adjacent_slot(open_day, service):
    service.buffer_after_minutes = 15
    service.save()
    customer = Customer.objects.create(first_name="Ada", last_name="Lovelace", email="ada@example.com", phone="5145550100")
    Appointment.objects.create(
        customer=customer,
        service=service,
        starts_at=aware_at(open_day, 10),
        ends_at=aware_at(open_day, 11),
        status='confirmed',
        quoted_price=service.price,
    )

    shorter_service = service
    shorter_service.duration_minutes = 30
    slots = AvailabilityService.get_available_slots(shorter_service, open_day)
    slot_times = {slot['time_str'] for slot in slots}

    assert '11:00' not in slot_times
    assert '11:30' in slot_times


def test_booking_revalidates_and_rejects_duplicate_slot(open_day, service, settings):
    settings.BOOKING_MIN_NOTICE_HOURS = 0
    customer_data = {
        'first_name': 'Maya',
        'last_name': 'Dubois',
        'email': 'MAYA@EXAMPLE.COM',
        'phone': ' 514 555 0101 ',
    }
    starts_at = aware_at(open_day, 13)

    appointment = AvailabilityService.book_appointment(customer_data, service, starts_at)

    assert appointment.customer.email == 'maya@example.com'
    with pytest.raises(SlotUnavailableError):
        AvailabilityService.book_appointment(customer_data, service, starts_at)


def test_blocked_period_requires_end_after_start(open_day):
    block = BlockedPeriod(starts_at=aware_at(open_day, 12), ends_at=aware_at(open_day, 11))

    with pytest.raises(ValidationError):
        block.full_clean()
