import json
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch
import pytest
from PIL import Image
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.services.models import ClientType, HairstyleSubcategory, HairstyleOptionGroup, HairstyleOptionValue, HairstyleOptionAssignment
from apps.services.services.configuration import calculate_service_price, calculate_service_duration, resolve_configuration
from apps.bookings.models import Appointment
from tests.conftest import aware_at

pytestmark = pytest.mark.django_db

@pytest.fixture
def selection(service):
    client_type = ClientType.objects.create(name='Client test', slug='client-test')
    return {'clientTypeId': str(client_type.pk), 'categoryId': str(service.pk), 'subcategoryId': None, 'selectedOptions': {}}


def make_group(service, kind='single_select', required=True, style=None):
    group = HairstyleOptionGroup.objects.create(name='Option test', slug=f'option-{HairstyleOptionGroup.objects.count()}', input_type=kind, is_required=required)
    HairstyleOptionAssignment.objects.create(category=service if not style else None, subcategory=style, option_group=group)
    value = HairstyleOptionValue.objects.create(option_group=group, label='Choix test', value='true', price_adjustment=20, duration_adjustment_minutes=30)
    return group, value


def test_pure_calculations():
    options = [{'priceAdjustment': '20.10', 'durationAdjustmentMinutes': 30}, {'priceAdjustment': '-5.05', 'durationAdjustmentMinutes': -10}]
    assert calculate_service_price('50', options) == Decimal('65.05')
    assert calculate_service_duration(60, options) == 80


def test_category_without_subcategory(selection):
    quote = resolve_configuration(selection)
    assert quote.price == Decimal('50')
    assert quote.duration_minutes == 60


def test_required_options_and_forged_price(service, selection):
    group, value = make_group(service)
    with pytest.raises(ValidationError):
        resolve_configuration(selection)
    selection['selectedOptions'] = {str(group.pk): str(value.pk)}
    selection['calculatedPrice'] = 1
    selection['calculatedDurationMinutes'] = 1
    quote = resolve_configuration(selection)
    assert quote.price == Decimal('70')
    assert quote.duration_minutes == 90
    value.is_active = False
    value.save()
    with pytest.raises(ValidationError):
        resolve_configuration(selection)


def test_style_required_and_inherited_group_override(service, selection):
    style = HairstyleSubcategory.objects.create(category=service, name='Style', slug='style')
    group, value = make_group(service)
    HairstyleOptionAssignment.objects.create(subcategory=style, option_group=group, is_required=False)
    with pytest.raises(ValidationError):
        resolve_configuration(selection)
    selection['subcategoryId'] = str(style.pk)
    assert resolve_configuration(selection).price == 50
    selection['selectedOptions'] = {str(group.pk): str(value.pk)}
    assert resolve_configuration(selection).price == 70  # inherited option counted once


def test_invalid_category_and_style_options(service, selection):
    style = HairstyleSubcategory.objects.create(category=service, name='Style', slug='style')
    other = HairstyleSubcategory.objects.create(category=service, name='Autre', slug='autre')
    group, value = make_group(service, style=style)
    selection.update(subcategoryId=str(other.pk), selectedOptions={str(group.pk): str(value.pk)})
    with pytest.raises(ValidationError):
        resolve_configuration(selection)


@pytest.mark.parametrize('kind,value', [('boolean', False), ('number', 0), ('text', 'Texte'), ('textarea', 'Notes')])
def test_required_value_types(service, selection, kind, value):
    group, _ = make_group(service, kind=kind)
    selection['selectedOptions'] = {str(group.pk): value}
    assert resolve_configuration(selection).snapshot['selectedOptions'][str(group.pk)] == value


def test_multi_select_rejects_duplicates(service, selection):
    group, value = make_group(service, kind='multi_select')
    selection['selectedOptions'] = {str(group.pk): [str(value.pk), str(value.pk)]}
    with pytest.raises(ValidationError):
        resolve_configuration(selection)


def test_upload_validation(service, selection):
    group, _ = make_group(service, kind='photo')
    key = f'option_file_{group.pk}'
    with pytest.raises(ValidationError):
        resolve_configuration(selection, {key: SimpleUploadedFile('fake.png', b'<script>bad</script>')}, True)
    with pytest.raises(ValidationError):
        resolve_configuration(selection, require_uploads=True)
    content = BytesIO()
    Image.new('RGB', (2, 2)).save(content, format='PNG')
    quote = resolve_configuration(selection, {key: SimpleUploadedFile('photo.png', content.getvalue())}, True)
    assert quote.uploads[0][2] == 'image/png'


def configure(client, selection):
    response = client.post('/reservation/configurer/', {'selection': json.dumps(selection)})
    assert response.status_code == 200, response.content
    return response.json()['token']


def test_calendar_requires_configuration(client, service):
    assert client.get('/reservation/disponibilites/calendrier/', {'service_id': service.pk}).status_code == 400


def test_configured_booking_duration_price_and_snapshot(client, service, selection, open_day, settings):
    settings.BOOKING_MIN_NOTICE_HOURS = 0
    group, value = make_group(service)
    selection['selectedOptions'] = {str(group.pk): str(value.pk)}
    token = configure(client, selection)
    slots = client.get('/reservation/disponibilites/', {'configuration_token': token, 'date': open_day.isoformat()})
    assert slots.status_code == 200
    assert b'15h30' in slots.content
    assert b'16h00' not in slots.content  # 90 minutes cannot finish before 17h
    client.get('/reservation/')
    with patch('apps.bookings.views.EmailService.send_notification', return_value=True):
        response = client.post('/reservation/', {
            'action': 'submit_booking', 'configuration_token': token, 'service_id': service.pk,
            'booking_nonce': client.session['booking_nonce'], 'slot': aware_at(open_day, 10).isoformat(),
            'date': open_day.isoformat(), 'first_name': 'Test', 'last_name': 'Client',
            'email': 'test@example.com', 'phone': '5145550101', 'accept_policy': 'on', 'calculatedPrice': '1',
        })
    assert response.status_code == 302
    appointment = Appointment.objects.get()
    assert appointment.quoted_price == 70
    assert (appointment.ends_at - appointment.starts_at).total_seconds() == 90 * 60
    assert appointment.configuration['options'][0]['value'] == 'Choix test'


def test_stale_quote_rejected(client, service, selection):
    token = configure(client, selection)
    service.price = 80
    service.save()
    assert client.get('/reservation/disponibilites/calendrier/', {'configuration_token': token}).status_code == 400


def test_token_is_session_bound(client, selection):
    token = configure(client, selection)
    from django.test import Client
    assert Client().get('/reservation/disponibilites/calendrier/', {'configuration_token': token}).status_code == 400


def test_final_booking_requires_configuration(client, service, open_day):
    client.get('/reservation/')
    response = client.post('/reservation/', {
        'action': 'submit_booking', 'service_id': service.pk,
        'booking_nonce': client.session['booking_nonce'], 'slot': aware_at(open_day, 10).isoformat(),
        'first_name': 'Test', 'last_name': 'Client', 'email': 'test@example.com', 'phone': '5145550101', 'accept_policy': 'on',
    })
    assert response.status_code == 200
    assert not Appointment.objects.exists()


def test_attachment_saved_privately_with_booking(client, service, selection, open_day, settings):
    from django.contrib.auth.models import User
    from apps.bookings.models import AppointmentAttachment
    settings.BOOKING_MIN_NOTICE_HOURS = 0
    group, _ = make_group(service, kind='photo')
    image = BytesIO()
    Image.new('RGB', (2, 2)).save(image, format='PNG')
    def upload():
        return SimpleUploadedFile('inspiration.png', image.getvalue(), content_type='image/png')
    field = f'option_file_{group.pk}'
    configured = client.post('/reservation/configurer/', {'selection': json.dumps(selection), field: upload()})
    assert configured.status_code == 200
    assert not AppointmentAttachment.objects.exists()  # temporary configuration does not store files
    client.get('/reservation/')
    payload = {'action': 'submit_booking', 'configuration_token': configured.json()['token'],
               'service_id': service.pk, 'booking_nonce': client.session['booking_nonce'],
               'slot': aware_at(open_day, 10).isoformat(), 'first_name': 'Test', 'last_name': 'Client',
               'email': 'test@example.com', 'phone': '5145550101', 'accept_policy': 'on'}
    assert client.post('/reservation/', payload).status_code == 200
    assert not Appointment.objects.exists()  # required file must actually be present
    payload[field] = upload()
    with patch('apps.bookings.views.EmailService.send_notification', return_value=True):
        response = client.post('/reservation/', payload)
    assert response.status_code == 302
    attachment = AppointmentAttachment.objects.get()
    url = f'/reservation/pieces-jointes/{attachment.pk}/'
    assert client.get(url).status_code == 302
    client.force_login(User.objects.create_user('ordinary'))
    assert client.get(url).status_code == 302
    client.force_login(User.objects.create_user('salon', is_staff=True))
    response = client.get(url)
    assert response.status_code == 200
    assert response.content == image.getvalue()
    assert response['Content-Disposition'].startswith('attachment;')


def test_invalid_form_keeps_configuration(client, service, selection, open_day):
    token = configure(client, selection)
    client.get('/reservation/')
    response = client.post('/reservation/', {
        'action': 'submit_booking', 'service_id': service.pk, 'configuration_token': token,
        'booking_nonce': client.session['booking_nonce'], 'slot': aware_at(open_day, 10).isoformat(),
        'first_name': 'Test', 'last_name': 'Client', 'email': 'invalid', 'phone': '5145550101', 'accept_policy': 'on',
    })
    assert response.status_code == 200
    assert response.context['configurator_initial']['step'] == 4
    assert response.context['configurator_initial']['token'] == token
    assert not Appointment.objects.exists()


def test_client_filter_and_catalogue_flags(client, service, selection):
    other = ClientType.objects.create(name='Autre', slug='autre')
    service.client_types.add(other)
    with pytest.raises(ValidationError):
        resolve_configuration(selection)
    response = client.get('/reservation/catalogue/')
    assert response.json()['categories'][0]['clientTypeIds'] == [str(other.pk)]
    service.is_active = False
    service.save()
    assert client.get('/reservation/catalogue/').json()['categories'] == []
