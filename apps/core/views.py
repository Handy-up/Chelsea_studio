from django.shortcuts import render
from apps.services.models import Service
from apps.gallery.models import GalleryItem
from apps.bookings.models import BusinessHours

def home_view(request):
    featured_services = Service.objects.filter(is_active=True, is_featured=True).select_related('category')[:4]
    if not featured_services:
        featured_services = Service.objects.filter(is_active=True).select_related('category')[:4]

    recent_gallery = GalleryItem.objects.filter(is_published=True).select_related('related_service')[:6]
    business_hours = BusinessHours.objects.all().order_by('weekday')

    context = {
        'featured_services': featured_services,
        'recent_gallery': recent_gallery,
        'business_hours': business_hours,
        'meta_title': "Chelsea Coiffure - Coiffeuse Privée & Réservation en Ligne",
        'meta_description': "Découvrez les prestations de Chelsea : coupes hommes et femmes, soins sur mesure. Réservez votre créneau directement en ligne !",
    }
    return render(request, 'core/home.html', context)

def privacy_policy_view(request):
    return render(request, 'core/privacy_policy.html', {'meta_title': "Politique de Confidentialité - Chelsea Coiffure"})

def cancellation_policy_view(request):
    return render(request, 'core/cancellation_policy.html', {'meta_title': "Politique d'Annulation - Chelsea Coiffure"})

def terms_view(request):
    return render(request, 'core/terms.html', {'meta_title': "Conditions Générales - Chelsea Coiffure"})
