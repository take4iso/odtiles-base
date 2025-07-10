"""
URL configuration for odtiles project.

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
from django.contrib import admin
from django.urls import path, re_path, include
from django.http import HttpResponse
from xyz import views as xyz_views
from upload import views as upload_views

def index(request):
    with open('odtiles/index.html', 'rb') as f:
        return HttpResponse(f.read(), content_type='text/html', charset='utf-8')

urlpatterns = [
    # XYZ Tile Service
    re_path(r'^xyz/.*/[0-9]+/[0-9]+/[0-9]+\.png$', xyz_views.tileimage, name='tileimage'),
    re_path(r'upload/.*', upload_views.geotiff_upload, name='upload'),
    path('', index, name='index'),
]
