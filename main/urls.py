from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

app_name = "main"

urlpatterns = [
    path(route="", view=views.dashboard, name="dashboard"),
    path(route="announcement/", view=views.announcement_list, name="announcement_list"),
    path(route="announcements/create/", view=views.create_announcement, name="create_announcement"),
    path(route="announcements/<int:pk>/edit/", view=views.edit_announcement, name="edit_announcement"),
    path(route="announcements/<int:pk>/delete/", view=views.delete_announcement, name="delete_announcement"),

    path('hello/', views.hello, name='hello'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
