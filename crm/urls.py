from django.contrib import admin
from django.urls import path
from crm.views import index,checkout,checkout_view

urlpatterns = [
    path('', index, name='index'),
    path('checkout/', checkout, name='checkout'),  # Assuming checkout uses the same view for simplicity
    path('checkout_view',checkout_view, name='checkout_view'),  # Adjusted to match the view function
    path('admin/', admin.site.urls),
]
