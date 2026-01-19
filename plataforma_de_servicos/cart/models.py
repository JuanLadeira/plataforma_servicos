from django.db import models
from django.utils import timezone
from datetime import timedelta

from plataforma_de_servicos.produto.models import Produto, VariacaoProduto


class ReservaEstoque(models.Model):
    """
    Modelo para reservar temporariamente estoque enquanto o item está no carrinho
    """
    session_key = models.CharField(max_length=40, help_text="Chave da sessão do usuário")
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, null=True, blank=True)
    variacao_produto = models.ForeignKey(VariacaoProduto, on_delete=models.CASCADE, null=True, blank=True)
    quantidade = models.PositiveIntegerField()
    criado_em = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        verbose_name = "Reserva de Estoque"
        verbose_name_plural = "Reservas de Estoque"
        constraints = [
            models.UniqueConstraint(
                fields=['session_key', 'produto'],
                name='unique_reserva_produto_sem_variacao',
                condition=models.Q(variacao_produto__isnull=True)
            ),
            models.UniqueConstraint(
                fields=['session_key', 'variacao_produto'],
                name='unique_reserva_variacao'
            ),
        ]
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            # Reserva por 30 minutos
            self.expires_at = timezone.now() + timedelta(minutes=30)
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.variacao_produto:
            return f"Reserva: {self.variacao_produto} - Qtd: {self.quantidade}"
        else:
            return f"Reserva: {self.produto} - Qtd: {self.quantidade}"
    
    @classmethod
    def limpar_expiradas(cls):
        """Remove reservas expiradas"""
        return cls.objects.filter(expires_at__lt=timezone.now()).delete()
    
    @classmethod
    def get_quantidade_reservada(cls, produto=None, variacao_produto=None):
        """Retorna a quantidade total reservada para um produto ou variação"""
        cls.limpar_expiradas()  # Limpa reservas expiradas primeiro
        
        if variacao_produto:
            return cls.objects.filter(variacao_produto=variacao_produto).aggregate(
                total=models.Sum('quantidade')
            )['total'] or 0
        elif produto:
            return cls.objects.filter(produto=produto).aggregate(
                total=models.Sum('quantidade')
            )['total'] or 0
        return 0
