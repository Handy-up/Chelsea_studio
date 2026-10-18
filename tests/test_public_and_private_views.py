import pytest
from django.contrib.auth.models import User

from apps.bookings.models import Appointment, Customer
from apps.gallery.models import GalleryItem
from tests.conftest import aware_at


pytestmark = pytest.mark.django_db


def test_public_core_urls_render(client):
    for url in ['/', '/services/', '/services/hommes/', '/services/femmes/', '/galerie/', '/politique-confidentialite/', '/politique-annulation/', '/conditions/']:
        response = client.get(url)
        assert response.status_code == 200, url


def test_homepage_uses_visual_hero_and_no_visible_phone(client):
    """
    La page d'accueil ne propose plus de gros choix de catégories Hommes/Femmes :
    ce filtre vit désormais uniquement sur la page des services (`/services/`).
    """
    response = client.get('/')
    content = response.content.decode()

    assert 'chelsea-salon-banner.webp' in content
    assert 'Choisissez votre catégorie' not in content
    assert '/services/' in content
    assert 'aria-label="Ouvrir Instagram"' in content
    assert 'Prendre rendez-vous en ligne' in content
    assert "Voir l'horaire" in content
    assert 'Contacter Chelsea' not in content
    assert 'tel:' not in content
    assert 'En direct' not in content


def test_service_filters_by_audience(client, service):
    response = client.get('/services/femmes/')

    assert response.status_code == 200
    assert service.name.encode() in response.content


def test_gallery_filter_renders(client, service):
    GalleryItem.objects.create(title="Coupe publiée", audience="women", related_service=service, is_published=True)

    response = client.get('/galerie/?audience=women')

    assert response.status_code == 200
    assert b'Coupe publi' in response.content


def test_gestion_requires_staff_login(client):
    response = client.get('/gestion/')

    assert response.status_code == 302
    assert '/gestion/connexion/' in response['Location']


def test_staff_can_open_gestion_dashboard(client):
    user = User.objects.create_user(username='chelsea', password='secret', is_staff=True)
    client.force_login(user)

    response = client.get('/gestion/')

    assert response.status_code == 200
    assert b'Tableau de bord' in response.content


def test_staff_can_confirm_appointment(client, open_day, service):
    user = User.objects.create_user(username='chelsea', password='secret', is_staff=True)
    client.force_login(user)
    customer = Customer.objects.create(first_name="Maya", last_name="Dubois", email="maya@example.com", phone="5145550101")
    appointment = Appointment.objects.create(
        customer=customer,
        service=service,
        starts_at=aware_at(open_day, 10),
        ends_at=aware_at(open_day, 11),
        status='pending',
        quoted_price=service.price,
    )

    response = client.post(f'/gestion/rendez-vous/{appointment.public_id}/', {'action': 'confirm'})

    assert response.status_code == 302
    appointment.refresh_from_db()
    assert appointment.status == 'confirmed'
