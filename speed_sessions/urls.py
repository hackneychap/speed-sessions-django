from django.contrib import admin
from django.urls import path, include
from workouts.views import home_view, signup_view, profile_view
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('trash-hq-69/', admin.site.urls),
    path('', home_view, name='home'),
    path('signup/', signup_view, name='signup'),
    path('profile/', profile_view, name='profile'),
    path('communities/', include('communities.urls')),
    path('merch/', include('merch.urls')),
    path('stripe/', include('djstripe.urls', namespace='djstripe')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('api/', include('workouts.urls')),
    path('planner/', include('session_planner.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
