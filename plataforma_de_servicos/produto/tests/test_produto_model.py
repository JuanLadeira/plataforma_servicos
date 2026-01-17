import pytest
from .factories import ProdutoFactory
from ..models import Image

pytestmark = pytest.mark.django_db


def test_produto_str():
    produto = ProdutoFactory(produto="Teste")
    assert str(produto) == "Teste"


def test_produto_get_absolute_url():
    # Corrigindo o teste para usar o nome do produto e a URL correta
    produto = ProdutoFactory(produto="Teste Slug")
    assert produto.get_absolute_url() == "/produto/teste-slug/"


def test_get_image_with_images(produto_factory):
    produto = produto_factory()
    image1 = Image.objects.create(produto=produto, image="produtos/img1.jpg", order=1)
    Image.objects.create(produto=produto, image="produtos/img2.jpg", order=2)

    assert produto.get_image() == image1.image.url


def test_get_image_no_images(produto_factory):
    # Criando um produto sem categoria para testar a imagem padrão genérica
    produto = produto_factory(categoria=None)
    assert produto.get_image() == "/static/images/default-outro.svg"


def test_get_images_with_images(produto_factory):
    produto = produto_factory()
    image1 = Image.objects.create(produto=produto, image="produtos/img1.jpg")
    image2 = Image.objects.create(produto=produto, image="produtos/img2.jpg")

    urls = produto.get_images()
    assert len(urls) == 2
    assert image1.image.url in urls
    assert image2.image.url in urls


def test_get_images_no_images(produto_factory):
    produto = produto_factory()
    assert produto.get_images() is None


def test_get_stock_range(produto_factory):
    # Este teste precisa ser adaptado, pois 'estoque' agora está na variação
    # Vamos simular um estoque no produto para testar a função como está
    produto = produto_factory()
    produto.estoque = 10
    produto.save()

    stock_range = produto.get_stock_range()
    assert len(stock_range) == 10
    assert stock_range[0] == "1"
    assert stock_range[-1] == "10"


def test_get_stock_range_max_20(produto_factory):
    produto = produto_factory()
    produto.estoque = 30
    produto.save()

    stock_range = produto.get_stock_range()
    assert len(stock_range) == 20
    assert stock_range[-1] == "20"
