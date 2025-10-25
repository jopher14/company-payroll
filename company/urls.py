"""
URL configuration for company project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from typing import cast, Any
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    # admin app
    path("admin/", admin.site.urls),

    # main app
    path("", include('main.urls')),

    # users app
    path("users/", include("users.urls", namespace="users")),

    # payroll app
    path('payroll/', include('payroll.urls')),

    path(route=".well-known/appspecific/com.chrome.devtools.json", view=views.chrome_devtools_config),

     path('api/', include('main.urls')),
     path('set-csrf/', views.set_csrf_token, name='set-csrf'),
     path('api/protected/', views.protected_view, name='protected'),

]

if settings.DEBUG:
    urlpatterns += cast(Any, static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT))
