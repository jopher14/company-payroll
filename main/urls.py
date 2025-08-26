from django.urls import path
from . import views

app_name = "main"

urlpatterns = [
    path(route="", view=views.dashboard, name="dashboard"),

    path(route="announcements/create/", view=views.create_announcement, name="create_announcement"),
    path(route="announcement/", view=views.announcement_list, name="announcement_list"),
]
