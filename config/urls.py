from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('', include('accounts.urls')),
    path('', include('organizations.urls')),
    path('books/', include('books.urls', namespace='books')),
    path('members/', include('members.urls', namespace='members')),
    path('transactions/', include('transactions.urls', namespace='transactions')),
    path('reservations/', include('reservations.urls', namespace='reservations')),
    path('reports/', include('reports.urls', namespace='reports')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
    path('subscriptions/', include('subscriptions.urls', namespace='subscriptions')),
    path('audit/', include('audit.urls', namespace='audit')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
