from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
    path('services/', include('apps.services.urls')),
    path('galerie/', include('apps.gallery.urls')),
    path('reservation/', include('apps.bookings.urls')),
    path('gestion/', include('apps.accounts.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler404 = 'apps.core.views_errors.custom_404_view'
handler500 = 'apps.core.views_errors.custom_500_view'
