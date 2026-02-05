from django.db import models
from django.contrib.auth import get_user_model

from plataforma_de_servicos.produto.models import Produto, VariacaoProduto

User = get_user_model()


class ShippingAddress(models.Model):

    full_name = models.CharField(max_length=300)

    email = models.EmailField(max_length=255)

    address1 = models.CharField(max_length=300)

    address2 = models.CharField(max_length=300)

    city = models.CharField(max_length=255)


    # Optional

    state = models.CharField(max_length=255, null=True, blank=True)

    zipcode = models.CharField(max_length=255, null=True, blank=True)


    # FK

    # Authenticated / not authenticated users (bear in mind)

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)



    class Meta:

        verbose_name_plural = 'Shipping Address'



    def __str__(self):

        return 'Shipping Address - ' + str(self.id)



class Order(models.Model):

    empresa = models.ForeignKey(
        "empresa.Empresa",
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name="Empresa",
        null=True,  # Temporary: remove after data migration
        blank=True,
    )

    full_name = models.CharField(max_length=300)

    email = models.EmailField(max_length=255)

    shipping_address = models.TextField(max_length=10000)


    amount_paid = models.DecimalField(max_digits=8, decimal_places=2)




    date_ordered = models.DateTimeField(auto_now_add=True)


    # FK

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)



    def __str__(self):

        return 'Order - #' + str(self.id)




class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True)
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, null=True)
    variacao_produto = models.ForeignKey(VariacaoProduto, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveBigIntegerField(default=1)
    price = models.DecimalField(max_digits=8, decimal_places=2)    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        if self.variacao_produto:
            return f'Order Item #{self.id} - {self.variacao_produto}'
        else:
            return f'Order Item #{self.id} - {self.produto}'



        