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


class VariacaoProdutoFactory(DjangoModelFactory):
    class Meta:
        model = VariacaoProduto

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
            valor_cor = ValorAtributoFactory(atributo=cor_attr, valor="Azul")
            self.valores.add(valor_cor)

    @factory.post_generation
    def gerar_sku(self, create, extracted, **kwargs):
        if create:
            self.gerar_sku()

