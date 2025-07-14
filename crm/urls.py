from django.contrib import admin
from django.urls import path
from crm.views import index

urlpatterns = [
    path('', index, name='index'),
    path('checkout/', index, name='checkout'),  # Assuming checkout uses the same view for simplicity
    path('admin/', admin.site.urls),
]
