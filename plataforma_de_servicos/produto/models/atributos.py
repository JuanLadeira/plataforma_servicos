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
    
    # Modificadores de preço
    preco_adicional = models.DecimalField(
        "Preço adicional", 
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Valor fixo a ser adicionado ao preço base (ex: R$ 5,00)"
    )
    percentual_adicional = models.DecimalField(
        "Percentual adicional", 
        max_digits=5, 
        decimal_places=2, 
        default=0,
        help_text="Percentual a ser adicionado ao preço base (ex: 10,00 para 10%)"
    )

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
    preco = models.DecimalField("preço", max_digits=10, decimal_places=2, null=True, blank=True)
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
            # Otimização: usar select_related para evitar query adicional no produto.slug
            # e prefetch_related para valores se necessário
            valores_ids = sorted(
                self.valores.only('id').values_list("id", flat=True)
            )
            if valores_ids:
                produto_slug = self.produto.slug if hasattr(self.produto, 'slug') else str(self.produto.pk)
                new_sku = f"{produto_slug}-" + "-".join(map(str, valores_ids))
                
                # Proteção contra loop infinito: só salvar se o SKU realmente mudou
                if self.sku != new_sku:
                    self.sku = new_sku
                    # Usar update em vez de save para evitar disparo de signals/hooks
                    VariacaoProduto.objects.filter(pk=self.pk).update(sku=self.sku)

    def calcular_preco_final(self):
        """
        Calcula o preço final baseado no preço da variação + modificadores dos atributos.
        Se a variação não tiver preço definido, usa o preço base do produto.
        """
        from decimal import Decimal
        
        # Preço base (da variação ou do produto)
        preco_base = self.preco or self.produto.preco or Decimal('0')
        
        if not preco_base:
            return Decimal('0')
        
        # Aplicar modificadores dos valores de atributo
        preco_final = preco_base
        
        for valor_atributo in self.valores.all():
            # Adicionar valor fixo
            if valor_atributo.preco_adicional:
                preco_final += valor_atributo.preco_adicional
            
            # Adicionar percentual sobre o preço base original
            if valor_atributo.percentual_adicional:
                preco_final += preco_base * (valor_atributo.percentual_adicional / Decimal('100'))
        
        return preco_final.quantize(Decimal('0.01'))

    def get_preco_display(self):
        """
        Retorna o preço formatado para exibição.
        """
        preco = self.calcular_preco_final()
        return f"R$ {preco:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
