from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView

urlpatterns = [
    # Built-in Django Admin
    path('django-admin/', admin.site.urls),
    # Redirect /admin/ to /admin-dashboard/ so user never hits a 404
    path('admin/', RedirectView.as_view(url='/admin-dashboard/', permanent=False)),
    # Store and Custom Admin Dashboard
    path('', include('store.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
