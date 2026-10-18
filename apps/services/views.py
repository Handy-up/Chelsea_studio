from django.shortcuts import render, get_object_or_404
from apps.services.models import Service, ServiceCategory

def service_list_view(request, audience=None):
    services_qs = Service.objects.filter(is_active=True).select_related('category')

    # Si audience spécifiée dans l'URL (ex: /services/hommes/ ou /services/femmes/) ou paramètre GET ?audience=
    filter_audience = audience or request.GET.get('audience')

    if filter_audience in ['men', 'women']:
        services_qs = services_qs.filter(category__audience__in=[filter_audience, 'unisex'])

    categories = ServiceCategory.objects.filter(is_active=True).prefetch_related('services')

    context = {
        'services': services_qs,
        'categories': categories,
        'current_audience': filter_audience or 'all',
        'meta_title': "Catalogue des Services - Chelsea Coiffure",
        'meta_description': "Consultez nos prestations coiffure Hommes et Femmes : tarifs, durées et conseils de préparation.",
    }

    # Si requête HTMX, retourner uniquement le fragment partial
    if request.headers.get('HX-Request'):
        return render(request, 'services/partials/service_list.html', context)

    return render(request, 'services/service_list.html', context)


def service_detail_view(request, slug):
    service = get_object_or_404(Service.objects.prefetch_related('images'), slug=slug, is_active=True)
    
    context = {
        'service': service,
        'meta_title': f"{service.name} - Chelsea Coiffure",
        'meta_description': service.short_description or f"Détails du service {service.name}.",
    }
    return render(request, 'services/service_detail.html', context)
