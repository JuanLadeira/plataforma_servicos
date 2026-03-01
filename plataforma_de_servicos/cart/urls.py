
from django.urls import path

from plataforma_de_servicos.cart import views

app_name = "cart"
urlpatterns = [
    path("", views.cart_summary, name="cart-summary"),
    path("add/", views.cart_add, name="cart-add"),
    path("delete/", views.cart_delete, name="cart-delete"),
    path("delete-mini/", views.cart_delete_mini, name="cart-delete-mini"),
    path("update/", views.cart_update, name="cart-update"),
    path("mini/", views.cart_mini, name="cart-mini"),
    path("increment/", views.cart_increment, name="cart-increment"),
    path("decrement/", views.cart_decrement, name="cart-decrement"),
]
