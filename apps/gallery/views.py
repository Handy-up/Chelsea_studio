from django.shortcuts import render
from apps.gallery.models import GalleryItem

def gallery_list_view(request):
    items_qs = GalleryItem.objects.filter(is_published=True).select_related('related_service')
    
    audience = request.GET.get('audience')
    if audience in ['men', 'women']:
        items_qs = items_qs.filter(audience__in=[audience, 'unisex'])

    context = {
        'gallery_items': items_qs,
        'current_audience': audience or 'all',
        'meta_title': "Galerie des Réalisations - Chelsea Coiffure",
        'meta_description': "Découvrez les réalisations et coupes réalisées par Chelsea en images.",
    }

    if request.headers.get('HX-Request'):
        return render(request, 'gallery/partials/gallery_grid.html', context)

    return render(request, 'gallery/gallery_list.html', context)
