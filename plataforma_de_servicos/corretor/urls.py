from django.urls import path

from . import views

app_name = "corretor"

urlpatterns = [
    path("interesse/", views.interesse_compra_view, name="interesse-compra"),
    path("interesse/sucesso/<int:interesse_id>/", views.interesse_sucesso_view, name="interesse-sucesso"),
]
