import factory
from factory import Faker
from factory.django import DjangoModelFactory

from ...models import Atributo, ValorAtributo, VariacaoProduto
from .produto_factory import ProdutoFactory


class AtributoFactory(DjangoModelFactory):
    class Meta:
        model = Atributo
        django_get_or_create = ('nome',)

    nome = factory.Iterator(["Cor", "Tamanho", "Material"])


class ValorAtributoFactory(DjangoModelFactory):
    class Meta:
        model = ValorAtributo
        django_get_or_create = ('atributo', 'valor',)

    atributo = factory.SubFactory(AtributoFactory)
    valor = factory.LazyAttribute(
        lambda obj: "Vermelho" if obj.atributo.nome == "Cor"
        else ("M" if obj.atributo.nome == "Tamanho" else "Algodão")
    )
    preco_adicional = 0
    percentual_adicional = 0


class VariacaoProdutoFactory(DjangoModelFactory):
    class Meta:
        model = VariacaoProduto
        skip_postgeneration_save = True

    produto = factory.SubFactory(ProdutoFactory)
    preco = Faker("pydecimal", left_digits=4, right_digits=2, positive=True)
    estoque = Faker("random_int", min=10, max=100)

    @factory.post_generation
    def valores(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for valor in extracted:
                self.valores.add(valor)
        else:
            # Cria um valor padrão se nenhum for passado
            cor_attr = AtributoFactory(nome="Cor")
            valor_cor = ValorAtributoFactory(
                atributo=cor_attr, 
                valor="Azul",
                preco_adicional=0,
                percentual_adicional=0
            )
            self.valores.add(valor_cor)

    @factory.post_generation
    def gerar_sku(self, create, extracted, **kwargs):
        # Otimização: só gerar SKU se não for um build (create=True) 
        # e se não estamos em testes que não precisam do SKU
        if create and not kwargs.get('skip_sku', False):
            # Defer SKU generation para evitar queries desnecessárias em testes
            try:
                # Evitar loop infinito: verificar se SKU já existe antes de gerar
                if not self.sku and self.pk and self.valores.exists():
                    self.gerar_sku()
            except Exception:
                # Em caso de erro (ex: produto sem slug), ignora
                pass

