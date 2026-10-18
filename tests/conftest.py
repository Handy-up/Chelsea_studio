from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from apps.bookings.models import BusinessHours
from apps.core.models import SiteSettings
from apps.services.models import Service, ServiceCategory


@pytest.fixture
def business_tz():
    return ZoneInfo("America/Toronto")


@pytest.fixture
def open_day(db, business_tz):
    settings = SiteSettings.get_solo()
    settings.timezone = "America/Toronto"
    settings.save()

    target = timezone.localdate() + timedelta(days=3)
    BusinessHours.objects.update_or_create(
        weekday=target.weekday(),
        defaults={
            'opening_time': time(9, 0),
            'closing_time': time(17, 0),
            'is_closed': False,
        },
    )
    return target


@pytest.fixture
def service(db):
    category = ServiceCategory.objects.create(
        name="Femmes",
        slug="femmes-test",
        audience="women",
        is_active=True,
    )
    return Service.objects.create(
        category=category,
        name="Coupe test",
        slug="coupe-test",
        short_description="Coupe de test",
        price=50,
        duration_minutes=60,
        buffer_before_minutes=0,
        buffer_after_minutes=0,
        is_active=True,
    )


def aware_at(day, hour, minute=0, tz=None):
    tz = tz or ZoneInfo("America/Toronto")
    return timezone.make_aware(datetime.combine(day, time(hour, minute)), tz)
