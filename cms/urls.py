from django.contrib import admin
from django.urls import path

from cms.views import index

urlpatterns = [
    path('/cms', index, name='index'),
]
