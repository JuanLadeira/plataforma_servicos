from django.db import models
from django_extensions.db.models import AutoSlugField

from .produto_model import Produto


class Atributo(models.Model):
    """
    Modelo para armazenar os tipos de atributos, como 'Cor' ou 'Tamanho'.
    """
    nome = models.CharField(max_length=50, unique=True, help_text="Ex: Cor, Tamanho")
    slug = AutoSlugField(populate_from="nome", unique=True)

    class Meta:
        verbose_name = "Atributo"
        verbose_name_plural = "Atributos"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class ValorAtributo(models.Model):
    """
    Modelo para armazenar os valores de um atributo, como 'Vermelho' para 'Cor'.
    """
    atributo = models.ForeignKey(Atributo, on_delete=models.CASCADE, related_name="valores")
    valor = models.CharField(max_length=50, help_text="Ex: Vermelho, P, 42")

    class Meta:
        verbose_name = "Valor de Atributo"
        verbose_name_plural = "Valores de Atributos"
        ordering = ["atributo", "valor"]
        unique_together = [["atributo", "valor"]]

    def __str__(self):
        return f"{self.atributo.nome}: {self.valor}"


class VariacaoProduto(models.Model):
    """
    Representa uma variação específica de um produto (SKU),
    baseada em uma combinação de valores de atributos.
    """
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name="variacoes")
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text="Stock Keeping Unit. Se deixado em branco, será gerado automaticamente.")
    preco = models.DecimalField("preço", max_digits=10, decimal_places=2)
    estoque = models.PositiveIntegerField("estoque atual", default=0)
    valores = models.ManyToManyField(ValorAtributo, related_name="variacoes")

    class Meta:
        verbose_name = "Variação de Produto"
        verbose_name_plural = "Variações de Produto"
        ordering = ["produto", "preco"]

    def __str__(self):
        # Acessa os valores após estarem disponíveis
        if self.pk:
            valores_str = " | ".join(str(valor) for valor in self.valores.all())
            return f"{self.produto.produto} ({valores_str})"
        return f"{self.produto.produto}"

    def save(self, *args, **kwargs):
        """
        Gera um SKU automaticamente se não for fornecido.
        O SKU é composto pelo slug do produto e os IDs dos valores de atributo.
        """
        # A geração do SKU depende da relação ManyToMany, que só é salva após o objeto principal.
        # Portanto, o SKU é gerado após o primeiro save.
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.sku:
            # É necessário um segundo save para construir o SKU com os IDs dos valores.
            # Isso pode ser melhorado com um signal post_save para evitar o duplo save aqui.
            pass

    def gerar_sku(self):
        """
        Método separado para gerar e salvar o SKU.
        Deve ser chamado após os valores ManyToMany serem adicionados.
        """
        if not self.sku and self.pk:
            valores_ids = sorted(self.valores.all().values_list("id", flat=True))
            if valores_ids:
                self.sku = f"{self.produto.slug}-" + "-".join(map(str, valores_ids))
                self.save(update_fields=['sku'])
